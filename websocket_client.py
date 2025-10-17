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
import re
import requests
import websocket
import threading
import time
import logging
import os
from typing import Dict, Any, Optional
from urllib.parse import urlparse
from stompest.protocol import StompParser

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

        # Initialize STOMP parser for protocol-compliant frame parsing
        self.stomp_parser = StompParser(version='1.2')
        
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
        Handle incoming WebSocket messages using stompest protocol parser.

        Args:
            ws: WebSocket instance
            message: Raw message string
        """
        logger.debug(f"Received raw message: {message[:200]}...")

        # Handle heartbeat (just a newline)
        if message == '\n':
            logger.debug("Heartbeat received")
            return

        try:
            # The server sends incorrect content-length headers, so we remove them
            # to let stompest parse based on the null terminator instead
            message_cleaned = re.sub(r'content-length:[^\n]*\n', '', message, flags=re.IGNORECASE)

            # Convert to bytes if needed (websocket-client may send strings)
            message_bytes = message_cleaned.encode('utf-8') if isinstance(message_cleaned, str) else message_cleaned

            # Feed message to STOMP parser
            self.stomp_parser.add(message_bytes)

            # Process all available frames
            while self.stomp_parser.canRead():
                frame = self.stomp_parser.get()

                if frame.command == 'CONNECTED':
                    logger.info("✅ STOMP connection established")
                    logger.debug(f"CONNECTED headers: {frame.headers}")
                    self.connected = True
                    self.reconnect_attempts = 0
                    self.connection_established.set()

                elif frame.command == 'MESSAGE':
                    logger.debug(f"MESSAGE headers: {frame.headers}")

                    # Parse JSON body
                    try:
                        if frame.body:
                            body_str = frame.body.decode('utf-8')
                            logger.debug(f"Extracted JSON body: {body_str}")
                            payload = json.loads(body_str)
                            logger.info(f"✅ Parsed payload: {payload}")
                            self.handle_entity_update(payload)
                        else:
                            logger.warning("MESSAGE frame has empty body")
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON payload: {e}")
                        logger.debug(f"Frame body: {frame.body}")

                elif frame.command == 'ERROR':
                    logger.error(f"STOMP ERROR frame received")
                    logger.error(f"Headers: {frame.headers}")
                    logger.error(f"Body: {frame.body.decode('utf-8') if frame.body else 'N/A'}")

                else:
                    logger.debug(f"Received STOMP frame: {frame.command}")

        except Exception as e:
            logger.error(f"Error parsing STOMP frame: {e}", exc_info=True)
            logger.debug(f"Raw message: {message}")
    
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
            model = payload.get('model')
            removed = payload.get('removed', False)

            if entity_id is None or name is None:
                logger.warning(f"Incomplete entity update payload: {payload}")
                return

            logger.info(f"Received entity update: id={entity_id}, name='{name}', parentId={parent_id}")

            # Try updating both caches - the entity will exist in one of them
            if model == "location":
                if removed:
                    self.handle_location_remove(entity_id, name, parent_id)
                else:
                    self.handle_location_update(entity_id, name, parent_id)
            else:
                if removed:
                    self.handle_department_remove(entity_id, name, parent_id)
                else:
                    self.handle_department_update(entity_id, name, parent_id)

        except Exception as e:
            logger.error(f"Error handling entity update: {e}", exc_info=True)

    def handle_location_remove(self, entity_id: int, name: str, parent_id: int) -> bool:
        """
        Handle Location entity remove.

        Args:
            entity_id: Location ID
            name: Location name
            parent_id: Parent location ID (0 for root)

        Returns:
            True if location was remove, False if not found in cache
        """
        try:
            if not self.cache_manager or not self.cache_manager.is_initialized():
                logger.warning("Cache manager not initialized, cannot remove location")
                return False

            location_cache = self.cache_manager.get_location_cache()
            if not location_cache:
                logger.warning("Location cache not available")
                return False

            # Convert parent_id of 0 to None for root nodes
            parent_id_value = None if parent_id == 0 else parent_id

            # Update the node in cache
            success = location_cache.remove_node(entity_id, name, parent_id_value)

            if success:
                logger.info(f"✅ remove Location cache: id={entity_id}, name='{name}', parent={parent_id}")
                # Rebuild indices and paths for updated cache
                location_cache._build_indices()
                location_cache._compute_paths()

            return success

        except Exception as e:
            logger.error(f"Error remove location {entity_id}: {e}", exc_info=True)
            return False
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

    def handle_department_remove(self, entity_id: int, name: str, parent_id: int) -> bool:
        """
        Handle Department entity remove.

        Args:
            entity_id: Department ID
            name: Department name
            parent_id: Parent department ID (0 for root)

        Returns:
            True if department was remove, False if not found in cache
        """
        try:
            if not self.cache_manager or not self.cache_manager.is_initialized():
                logger.warning("Cache manager not initialized, cannot remove department")
                return False

            department_cache = self.cache_manager.get_department_cache()
            if not department_cache:
                logger.warning("Department cache not available")
                return False

            # Convert parent_id of 0 to None for root nodes
            parent_id_value = None if parent_id == 0 else parent_id

            # Update the node in cache
            success = department_cache.remove_node(entity_id, name, parent_id_value)

            if success:
                logger.info(f"✅ Updated Department cache: id={entity_id}, name='{name}', parent={parent_id}")
                # Rebuild indices and paths for remove cache
                department_cache._build_indices()
                department_cache._compute_paths()

            return success

        except Exception as e:
            logger.error(f"Error remove department {entity_id}: {e}", exc_info=True)
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