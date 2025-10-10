"""
API Client for Dynamic Form Schema

Fetches field definitions from external API and converts them to JSON Schema format.
"""

import httpx
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta


class FormSchemaCache:
    """Simple in-memory cache with TTL for form schemas."""
    
    def __init__(self, ttl_seconds: int = 300):
        """
        Initialize cache.
        
        Args:
            ttl_seconds: Time-to-live for cached entries (default: 5 minutes)
        """
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, tuple[Any, datetime]] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        if key in self._cache:
            value, expiry = self._cache[key]
            if datetime.now() < expiry:
                return value
            else:
                del self._cache[key]
        return None
    
    def set(self, key: str, value: Any):
        """Set cached value with expiry."""
        expiry = datetime.now() + timedelta(seconds=self.ttl_seconds)
        self._cache[key] = (value, expiry)
    
    def clear(self):
        """Clear all cached entries."""
        self._cache.clear()


class FormSchemaClient:
    """Client for fetching and parsing dynamic form schemas."""
    
    # Map API field types to JSON Schema types
    TYPE_MAPPING = {
        "TextFieldRest": "string",
        "TextAreaFieldRest": "string",
        "RichTextAreaFieldRest": "string",
        "NumberFieldRest": "number",
        "DropDownFieldRest": "string",
        "MultiSelectDropDownFieldRest": "array",
        "CheckBoxFieldRest": "array",
        "AttachmentFieldRest": "string",
        "SystemFieldRest": "string",
        "APIFieldRest": "string",
        "DisplayFieldRest": "string",
    }
    
    def __init__(self, api_url: str, cache_ttl: int = 300, verbose: bool = False):
        """
        Initialize the form schema client.
        
        Args:
            api_url: Base URL for the form schema API
            cache_ttl: Cache time-to-live in seconds (default: 5 minutes)
            verbose: Enable verbose logging
        """
        self.api_url = api_url
        self.cache = FormSchemaCache(ttl_seconds=cache_ttl)
        self.verbose = verbose
    
    async def fetch_form_schema(self, auth_token: Optional[str] = None, user_groups: Optional[List[int]] = None) -> Dict:
        """
        Fetch form schema from API with caching.
        
        Args:
            auth_token: Bearer token for authentication
            user_groups: List of user group IDs for permission filtering
            
        Returns:
            API response as dictionary
        """
        # Create cache key based on auth token (or "default" if none)
        # cache_key = f"schema_{auth_token[:20] if auth_token else 'default'}"
        #
        # # Check cache first
        # cached = self.cache.get(cache_key)
        # if cached:
        #     if self.verbose:
        #         print(f"[FormSchemaClient] Using cached schema for key: {cache_key}")
        #     return cached
        #
        if self.verbose:
            print(f"[FormSchemaClient] Fetching schema from API: {self.api_url}")
        
        # Fetch from API
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
        }
        
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        
        try:
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.get(self.api_url, headers=headers, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                
                # Cache the response
                # self.cache.set(cache_key, data)
                
                if self.verbose:
                    print(f"[FormSchemaClient] Successfully fetched schema with {len(data.get('fieldList', []))} fields")
                
                return data
                
        except Exception as e:
            if self.verbose:
                print(f"[FormSchemaClient] Error fetching schema: {e}")
            raise
    
    def filter_fields_by_permission(self, fields: List[Dict], user_groups: Optional[List[int]] = None) -> List[Dict]:
        """
        Filter fields based on user permissions.
        
        Args:
            fields: List of field definitions from API
            user_groups: List of user group IDs
            
        Returns:
            Filtered list of fields the user can access
        """
        filtered = []
        
        for field in fields:
            # Skip if field is hidden or removed
            if field.get("hidden", False) or field.get("removed", False) or field.get("inActive", False):
                continue
            
            # Check group-based permissions
            field_groups = field.get("groupIds", [])
            if field_groups and user_groups:
                # User must be in at least one of the field's groups
                if not any(group_id in user_groups for group_id in field_groups):
                    continue
            
            # Skip fields that are view-only and not editable
            if field.get("requesterViewOnly", False) and not field.get("requesterCanEdit", False):
                continue
            
            filtered.append(field)
        
        if self.verbose:
            print(f"[FormSchemaClient] Filtered {len(fields)} fields to {len(filtered)} accessible fields")
        
        return filtered
    
    def convert_to_json_schema(self, fields: List[Dict]) -> Dict:
        """
        Convert API field definitions to JSON Schema format.
        Wraps all dynamic fields inside a 'request_data' object parameter.

        Args:
            fields: List of filtered field definitions

        Returns:
            JSON Schema object with request_data wrapper
        """
        properties = {}
        required = []

        for field in fields:
            field_name = field.get("name", "")
            field_type = field.get("type", "")
            param_name = field.get("paramName", field_name.lower().replace(" ", "_").replace("-", "_"))

            # Get JSON Schema type
            json_type = self.TYPE_MAPPING.get(field_type, "string")

            # Build property definition
            prop = {"type": json_type}

            # Add description
            if field_name:
                prop["description"] = field_name

            # Ensure all array types have items property (required by JSON Schema spec)
            # This provides a default that may be overridden by specific field type logic below
            if json_type == "array" and "items" not in prop:
                prop["items"] = {"type": "string"}
                if self.verbose:
                    print(f"[FormSchemaClient] Added default items to array field: {param_name}")

            # Add enum for dropdown fields
            if field_type in ["DropDownFieldRest", "CheckBoxFieldRest", "MultiSelectDropDownFieldRest"]:
                options = field.get("options", [])
                if options:
                    if json_type == "array":
                        prop["items"] = {"type": "string", "enum": options}
                        if self.verbose:
                            print(f"[FormSchemaClient] Added enum items to array field: {param_name} ({len(options)} options)")
                    else:
                        prop["enum"] = options

            # Add default value
            if "defaultValue" in field:
                prop["default"] = field["defaultValue"]

            # Add min/max for number fields
            if field_type == "NumberFieldRest":
                if field.get("minLength", 0) > 0:
                    prop["minimum"] = field["minLength"]
                if field.get("maxLength", 0) > 0:
                    prop["maximum"] = field["maxLength"]

            # Add to properties
            properties[param_name] = prop

            # Check if required
            if field.get("required", False) or field.get("requesterRequired", False):
                required.append(param_name)

        # Wrap all fields inside request_data object
        inner_schema = {
            "type": "object",
            "properties": properties
        }

        if required:
            inner_schema["required"] = required

        # Create outer schema with request_data parameter
        schema = {
            "type": "object",
            "required": ["request_data"],
            "properties": {
                "request_data": inner_schema
            }
        }

        schema = inner_schema
        if self.verbose:
            print(f"[FormSchemaClient] Generated schema with {len(properties)} properties, {len(required)} required")

        return schema
    
    async def get_tool_schema(self, auth_token: Optional[str] = None, user_groups: Optional[List[int]] = None) -> Dict:
        """
        Get complete tool schema for create_request.
        
        Args:
            auth_token: Bearer token for authentication
            user_groups: List of user group IDs
            
        Returns:
            JSON Schema for the tool
        """
        try:
            # Fetch form schema
            form_data = await self.fetch_form_schema(auth_token, user_groups)
            
            # Get field list
            fields = form_data.get("fieldList", [])
            
            # Filter by permissions
            filtered_fields = self.filter_fields_by_permission(fields, user_groups)
            
            # Convert to JSON Schema
            schema = self.convert_to_json_schema(filtered_fields)
            
            return schema
            
        except Exception as e:
            if self.verbose:
                print(f"[FormSchemaClient] Error generating tool schema: {e}")
            
            # Return fallback schema with basic fields
            return {
                "type": "object",
                "required": ["subject", "requester"],
                "properties": {
                    "subject": {"type": "string", "description": "Subject"},
                    "requester": {"type": "string", "description": "Requester"},
                    "description": {"type": "string", "description": "Description"}
                }
            }

