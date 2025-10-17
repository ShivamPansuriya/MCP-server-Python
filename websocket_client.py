#!/usr/bin/env python3
"""
Hierarchy Cache WebSocket Client

WebSocket client for receiving real-time Location and Department entity updates
from the Motadata ITSM server and updating the hierarchy caches accordingly.

This client:
1. Authenticates using OAuth2 client_credentials grant
2. Obtains a WebSocket handshake token
3. Connects to the WebSocket server using STOMP protocol
4. Subscribes to python-service notifications
5. Processes Location and Department entity updates
6. Updates the hierarchy caches in real-time
"""

import json
import requests
import websocket
import threading
import time
import logging
import os
from typing import Dict, Any, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class HierarchyCacheWebSocketClient:
    """
    WebSocket client for hierarchy cache synchronization.
    
    Connects to Motadata ITSM WebSocket server and listens for Location and
    Department entity updates, applying them to the hierarchy caches in real-time.
    """
    
    def __init__(
        self,
        cache_manager,
        server_url: str,
        access_token: str,
        client_id: str = "python-service",
        client_secret: str = "IZqQXkqA1tGLIBRpYs",
        instance_id: str = "python-service-1"
    ):
        """
        Initialize the WebSocket client.
        
        Args:
            cache_manager: HierarchyCacheManager instance for cache updates
            server_url: Base URL of the Motadata server (e.g., https://your-server.com)
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret
            instance_id: Unique identifier for this service instance
        """
        self.cache_manager = cache_manager
        self.server_url = server_url.rstrip('/')
        self.client_id = client_id
        self.client_secret = client_secret
        self.instance_id = instance_id
        self.access_token = access_token
        self.ws: Optional[websocket.WebSocketApp] = None
        self.connected = False
        self.connection_established = threading.Event()
        self.connection_failed = threading.Event()
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self.reconnect_delay = 5  # seconds
        
    def authenticate(self) -> str:
        """
        Obtain OAuth2 access token using client_credentials grant.

        Returns:
            Access token string

        Raises:
            requests.HTTPError: If authentication fails
        """
        token_url = f"{self.server_url}/api/oauth/token"
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': self.client_id
        }

        logger.info(f"Authenticating with server: {token_url}")

        try:
            response = requests.post(token_url, data=data, timeout=10)
            response.raise_for_status()

            token_data = response.json()
            self.access_token = token_data['access_token']
            expires_in = token_data.get('expires_in', 172800)

            logger.info(f"Authentication successful. Token expires in {expires_in} seconds")
            return self.access_token
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Authentication failed: {e}")
            raise
    
    def get_handshake_token(self) -> str:
        """
        Get WebSocket handshake token from the server.
        
        Returns:
            Handshake token string
            
        Raises:
            requests.HTTPError: If token request fails
        """
        handshake_url = f"{self.server_url}/api/socket/handshake-token"
        headers = {'Authorization': f'Bearer {self.access_token}'}
        
        logger.info("Requesting WebSocket handshake token")
        
        try:
            response = requests.get(handshake_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            token = response.json()['token']
            logger.info("Handshake token obtained successfully")
            return token
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get handshake token: {e}")
            raise
    
    def on_message(self, ws, message):
        """
        Handle incoming WebSocket messages.
        
        Args:
            ws: WebSocket instance
            message: Raw message string
        """
        logger.debug(f"Received raw message: {message[:200]}...")
        
        # Parse STOMP frame
        if message.startswith("CONNECTED"):
            logger.info("✅ STOMP connection established")
            self.connected = True
            self.reconnect_attempts = 0
            self.connection_established.set()
            
        elif message.startswith("MESSAGE"):
            # Extract message body from STOMP frame
            lines = message.split('\n')
            body_start = False
            for line in lines:
                if body_start and line.strip():
                    try:
                        payload = json.loads(line)
                        self.handle_entity_update(payload)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON payload: {e}")
                        logger.debug(f"Problematic line: {line}")
                    break
                if line == '':
                    body_start = True
                    
        elif message.startswith("ERROR"):
            logger.error(f"STOMP error received: {message}")
            
        elif message == '\n':
            # Heartbeat
            logger.debug("Heartbeat received")
    
    def handle_entity_update(self, payload: Dict[str, Any]):
        """
        Process entity update notification and route to appropriate handler.

        The payload structure from the server is:
        {
            "id": <entity_id>,
            "parentId": <parent_id>,
            "name": "<entity_name>"
        }

        Since the server doesn't explicitly indicate entity type in the payload,
        we attempt to update both Location and Department caches. The update
        will succeed for whichever cache contains the entity.

        Args:
            payload: Entity update payload containing id, parentId, name
        """
        try:
            entity_id = payload.get('id')
            parent_id = payload.get('parentId', 0)  # Default to 0 if not provided
            name = payload.get('name')

            if entity_id is None or name is None:
                logger.warning(f"Incomplete entity update payload: {payload}")
                return

            logger.info(f"Received entity update: id={entity_id}, name='{name}', parentId={parent_id}")

            # Try updating both caches - the entity will exist in one of them
            location_updated = self.handle_location_update(entity_id, name, parent_id)
            department_updated = self.handle_department_update(entity_id, name, parent_id)

            if not location_updated and not department_updated:
                logger.warning(
                    f"Entity {entity_id} not found in either Location or Department cache. "
                    f"This might be a new entity that hasn't been loaded into cache yet."
                )

        except Exception as e:
            logger.error(f"Error handling entity update: {e}", exc_info=True)

    def handle_location_update(self, entity_id: int, name: str, parent_id: int) -> bool:
        """
        Handle Location entity update.

        Args:
            entity_id: Location ID
            name: Location name
            parent_id: Parent location ID (0 for root)

        Returns:
            True if location was updated, False if not found in cache
        """
        try:
            if not self.cache_manager or not self.cache_manager.is_initialized():
                logger.warning("Cache manager not initialized, cannot update location")
                return False

            location_cache = self.cache_manager.get_location_cache()
            if not location_cache:
                logger.warning("Location cache not available")
                return False

            # Convert parent_id of 0 to None for root nodes
            parent_id_value = None if parent_id == 0 else parent_id

            # Update the node in cache
            success = location_cache.update_node(entity_id, name, parent_id_value)

            if success:
                logger.info(f"✅ Updated Location cache: id={entity_id}, name='{name}', parent={parent_id}")
                # Rebuild indices and paths for updated cache
                location_cache._build_indices()
                location_cache._compute_paths()

            return success

        except Exception as e:
            logger.error(f"Error updating location {entity_id}: {e}", exc_info=True)
            return False

    def handle_department_update(self, entity_id: int, name: str, parent_id: int) -> bool:
        """
        Handle Department entity update.

        Args:
            entity_id: Department ID
            name: Department name
            parent_id: Parent department ID (0 for root)

        Returns:
            True if department was updated, False if not found in cache
        """
        try:
            if not self.cache_manager or not self.cache_manager.is_initialized():
                logger.warning("Cache manager not initialized, cannot update department")
                return False

            department_cache = self.cache_manager.get_department_cache()
            if not department_cache:
                logger.warning("Department cache not available")
                return False

            # Convert parent_id of 0 to None for root nodes
            parent_id_value = None if parent_id == 0 else parent_id

            # Update the node in cache
            success = department_cache.update_node(entity_id, name, parent_id_value)

            if success:
                logger.info(f"✅ Updated Department cache: id={entity_id}, name='{name}', parent={parent_id}")
                # Rebuild indices and paths for updated cache
                department_cache._build_indices()
                department_cache._compute_paths()

            return success

        except Exception as e:
            logger.error(f"Error updating department {entity_id}: {e}", exc_info=True)
            return False
    
    def on_error(self, ws, error):
        """Handle WebSocket errors."""
        logger.error(f"WebSocket error: {error}")
        self.connection_failed.set()
    
    def on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection close."""
        self.connected = False
        logger.warning(f"WebSocket closed: {close_status_code} - {close_msg}")
        
        # Attempt reconnection
        if self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            logger.info(
                f"Attempting reconnection {self.reconnect_attempts}/"
                f"{self.max_reconnect_attempts} in {self.reconnect_delay} seconds..."
            )
            time.sleep(self.reconnect_delay)
            self.connect()
        else:
            logger.error("Max reconnection attempts reached. Giving up.")
            self.connection_failed.set()
    
    def on_open(self, ws):
        """
        Send CONNECT and SUBSCRIBE frames after connection opens.
        
        Args:
            ws: WebSocket instance
        """
        logger.info("WebSocket connection opened")
        
        # Send CONNECT frame with authentication
        connect_headers = {
            "accept-version": "1.2",
            "heart-beat": "10000,10000",
        }
        connect_message = build_stomp_message("CONNECT", connect_headers)
        ws.send(connect_message)
        logger.info("CONNECT frame sent")
        
        # Wait for CONNECTED response
        time.sleep(1)
        
        # Send SUBSCRIBE frame
        subscribe_frame = (
            f"SUBSCRIBE\n"
            f"id:sub-0\n"
            f"destination:/users/execute-task/python-service\n"
            f"model:python_service\n"
            f"refid:1\n"
            f"\n"
            f"\x00"
        )
        ws.send(subscribe_frame)
        logger.info("Subscribed to /users/python-service/execute-task/python-service")
    
    def connect(self):
        """
        Establish WebSocket connection.

        This method:
        1. Authenticates to get OAuth2 token
        2. Gets WebSocket handshake token
        3. Connects to WebSocket endpoint (SockJS format)
        4. Starts message processing loop

        Note: The Spring WebSocket endpoint is configured with SockJS (.withSockJS()),
        so we need to use the SockJS WebSocket endpoint format: /endpoint/websocket
        """
        try:
            # Authenticate and get tokens
            self.authenticate()
            handshake_token = self.get_handshake_token()

            # Build WebSocket URL for SockJS
            # SockJS endpoints require /websocket suffix when using raw WebSocket
            # The server has /api context path, so the full path is /api/public/mtdtsocket/websocket
            parsed_url = urlparse(self.server_url)
            ws_scheme = 'wss' if parsed_url.scheme == 'https' else 'ws'

            # Build WebSocket URL with /api context path
            ws_url = f"{ws_scheme}://{parsed_url.netloc}/api/public/mtdtsocket/websocket?mtdt={handshake_token}"

            logger.info(f"Connecting to WebSocket (SockJS format): {ws_url}")

            # Create WebSocket connection
            self.ws = websocket.WebSocketApp(
                ws_url,
                header=[
                    "Authorization: Bearer " + self.access_token,
                ],
                on_open=self.on_open,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close
            )

            # Run WebSocket (blocking call)
            self.ws.run_forever()

        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self.connection_failed.set()
            raise

def build_stomp_message(command, headers=None, body=""):
    """
    Builds a STOMP message as per protocol
    """
    if headers is None:
        headers = {}
    message = command + "\n"
    for key, value in headers.items():
        message += f"{key}:{value}\n"
    message += "\n" + body + "\u0000"
    return message