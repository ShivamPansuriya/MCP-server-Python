"""
User Search Query Builder

Constructs Elasticsearch queries for fuzzy user search with field boosting
and userType filtering.
"""

import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class UserSearchQueryBuilder:
    """
    Builds Elasticsearch queries for user search with fuzzy matching.

    Supports:
    - Multi-field fuzzy search with configurable field boosting
    - UserType filtering (requester/technician)
    - Configurable fuzziness level (global and per-field)
    - Field-level min_score thresholds
    """

    # Valid userType values
    VALID_USER_TYPES = {"requester", "technician"}

    def __init__(
        self,
        field_boosts: Dict[str, float],
        fuzziness: str = "AUTO",
        field_fuzziness: Optional[Dict[str, str]] = None,
        field_min_scores: Optional[Dict[str, float]] = None
    ):
        """
        Initialize query builder.

        Args:
            field_boosts: Dictionary mapping field names to boost values
            fuzziness: Global fuzziness level (AUTO, 0, 1, 2)
            field_fuzziness: Optional dict of field-specific fuzziness overrides
            field_min_scores: Optional dict of field-specific min_score thresholds
        """
        self.field_boosts = field_boosts
        self.fuzziness = fuzziness
        self.field_fuzziness = field_fuzziness or {}
        self.field_min_scores = field_min_scores or {}

        logger.debug(
            f"UserSearchQueryBuilder initialized with {len(field_boosts)} fields, "
            f"global_fuzziness={fuzziness}, "
            f"field_overrides={len(self.field_fuzziness)} fuzziness, {len(self.field_min_scores)} min_scores"
        )
    
    def build_search_query(
        self,
        query: str,
        user_type: Optional[str] = None,
        size: int = 10
    ) -> Dict[str, Any]:
        """
        Build complete Elasticsearch search query.

        Args:
            query: Search query string
            user_type: Optional user type filter (requester/technician)
            size: Maximum number of results to return

        Returns:
            Elasticsearch query dictionary

        Raises:
            ValueError: If query is empty or user_type is invalid
        """
        if not query or not query.strip():
            raise ValueError("Search query cannot be empty")

        # Validate user_type if provided
        if user_type is not None:
            user_type_lower = user_type.lower()
            if user_type_lower not in self.VALID_USER_TYPES:
                raise ValueError(
                    f"Invalid user_type: {user_type}. "
                    f"Must be one of: {', '.join(self.VALID_USER_TYPES)}"
                )
            user_type = user_type_lower

        # Build the query
        es_query = {
            "size": size,
            "query": self._build_bool_query(query.strip(), user_type),
            "_source": [
                "dbid",
                "user_name",
                "user_email",
                "user_contact",
                "user_userlogonname",
                "user_contact2",
                "user_usertype"
            ]
        }

        logger.debug(f"Built search query for: '{query}', user_type={user_type}, size={size}")

        return es_query

    def build_field_specific_query(
        self,
        name: Optional[str] = None,
        email: Optional[str] = None,
        contact: Optional[str] = None,
        userlogonname: Optional[str] = None,
        contact2: Optional[str] = None,
        user_type: Optional[str] = None,
        size: int = 10,
        min_score: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Build Elasticsearch query for field-specific search.

        Args:
            name: Search by user name
            email: Search by email address
            contact: Search by primary contact
            userlogonname: Search by login name
            contact2: Search by secondary contact
            user_type: Optional user type filter (requester/technician)
            size: Maximum number of results to return
            min_score: Minimum confidence score threshold (e.g., 7.0)

        Returns:
            Elasticsearch query dictionary

        Raises:
            ValueError: If no search fields provided or user_type is invalid
        """
        # Collect field-specific queries
        field_queries = []

        if name:
            field_queries.append({
                "match": {
                    "user_name": {
                        "query": name,
                        "fuzziness": self.get_field_fuzziness("user_name"),  # Use field-specific fuzziness
                        "boost": self.field_boosts.get("user_name", 1.0)
                    }
                }
            })

        if email:
            field_queries.append({
                "match": {
                    "user_email": {
                        "query": email,
                        "fuzziness": self.get_field_fuzziness("user_email"),  # Use field-specific fuzziness
                        "boost": self.field_boosts.get("user_email", 1.0)
                    }
                }
            })

        if contact:
            field_queries.append({
                "match": {
                    "user_contact": {
                        "query": contact,
                        "fuzziness": self.get_field_fuzziness("user_contact"),  # Use field-specific fuzziness
                        "boost": self.field_boosts.get("user_contact", 1.0)
                    }
                }
            })

        if userlogonname:
            field_queries.append({
                "match": {
                    "user_userlogonname": {
                        "query": userlogonname,
                        "fuzziness": self.get_field_fuzziness("user_userlogonname"),  # Use field-specific fuzziness
                        "boost": self.field_boosts.get("user_userlogonname", 1.0)
                    }
                }
            })

        if contact2:
            field_queries.append({
                "match": {
                    "user_contact2": {
                        "query": contact2,
                        "fuzziness": self.get_field_fuzziness("user_contact2"),  # Use field-specific fuzziness
                        "boost": self.field_boosts.get("user_contact2", 1.0)
                    }
                }
            })

        if not field_queries:
            raise ValueError("At least one search field must be provided")

        # Validate user_type if provided
        if user_type is not None:
            user_type_lower = user_type.lower()
            if user_type_lower not in self.VALID_USER_TYPES:
                raise ValueError(
                    f"Invalid user_type: {user_type}. "
                    f"Must be one of: {', '.join(self.VALID_USER_TYPES)}"
                )
            user_type = user_type_lower

        # Build bool query
        bool_query = {
            "bool": {
                "should": field_queries,
                "minimum_should_match": 1
            }
        }

        # Add user_type filter if specified
        if user_type is not None:
            bool_query["bool"]["filter"] = [
                {
                    "term": {
                        "user_usertype": user_type
                    }
                }
            ]

        # Build complete query
        es_query = {
            "size": size,
            "query": bool_query,
            "_source": [
                "dbid",
                "user_name",
                "user_email",
                "user_contact",
                "user_userlogonname",
                "user_contact2",
                "user_usertype"
            ]
        }

        # Add minimum score filter if specified
        if min_score is not None and min_score > 0:
            es_query["min_score"] = min_score
            logger.debug(f"Applied minimum score filter: {min_score}")

        logger.debug(
            f"Built field-specific query: name={name}, email={email}, "
            f"contact={contact}, userlogonname={userlogonname}, "
            f"contact2={contact2}, user_type={user_type}, size={size}, "
            f"min_score={min_score}"
        )

        return es_query
    
    def _build_bool_query(
        self,
        query: str,
        user_type: Optional[str]
    ) -> Dict[str, Any]:
        """
        Build bool query with multi_match and optional user_type filter.
        
        Args:
            query: Search query string
            user_type: Optional user type filter
            
        Returns:
            Bool query dictionary
        """
        bool_query = {
            "bool": {
                "must": [
                    self._build_multi_match_query(query)
                ]
            }
        }
        
        # Add user_type filter if specified
        if user_type is not None:
            bool_query["bool"]["filter"] = [
                {
                    "term": {
                        "user_usertype": user_type
                    }
                }
            ]
        
        return bool_query
    
    def _build_multi_match_query(self, query: str) -> Dict[str, Any]:
        """
        Build multi_match query with fuzzy matching and field boosting.
        
        Args:
            query: Search query string
            
        Returns:
            Multi-match query dictionary
        """
        # Build fields list with boost values
        # Format: ["field_name^boost_value", ...]
        fields = [
            f"{field_name}^{boost}"
            for field_name, boost in self.field_boosts.items()
        ]
        
        multi_match_query = {
            "multi_match": {
                "query": query,
                "fields": fields,
                "fuzziness": self.fuzziness,
                "type": "best_fields",
                "operator": "or",
                "prefix_length": 0,
                "max_expansions": 50
            }
        }
        
        logger.debug(
            f"Multi-match query: fields={len(fields)}, "
            f"fuzziness={self.fuzziness}, query='{query}'"
        )
        
        return multi_match_query
    
    def validate_user_type(self, user_type: Optional[str]) -> Optional[str]:
        """
        Validate and normalize user_type value.

        Args:
            user_type: User type to validate

        Returns:
            Normalized user_type (lowercase) or None

        Raises:
            ValueError: If user_type is invalid
        """
        if user_type is None:
            return None

        user_type_lower = user_type.lower()
        if user_type_lower not in self.VALID_USER_TYPES:
            raise ValueError(
                f"Invalid user_type: {user_type}. "
                f"Must be one of: {', '.join(self.VALID_USER_TYPES)}"
            )

        return user_type_lower

    def get_field_fuzziness(self, field_name: str) -> str:
        """
        Get effective fuzziness for a specific field.

        Args:
            field_name: Name of the field

        Returns:
            Fuzziness value (field-specific or global)
        """
        return self.field_fuzziness.get(field_name, self.fuzziness)

    def get_field_min_score(self, field_name: str, global_min_score: float = 0.0) -> float:
        """
        Get effective min_score for a specific field.

        Args:
            field_name: Name of the field
            global_min_score: Global min_score threshold

        Returns:
            Min score value (field-specific or global)
        """
        return self.field_min_scores.get(field_name, global_min_score)


def create_query_builder(
    field_boosts: Dict[str, float],
    fuzziness: str = "AUTO",
    field_fuzziness: Optional[Dict[str, str]] = None,
    field_min_scores: Optional[Dict[str, float]] = None
) -> UserSearchQueryBuilder:
    """
    Factory function to create UserSearchQueryBuilder instance.

    Args:
        field_boosts: Dictionary mapping field names to boost values
        fuzziness: Global fuzziness level (AUTO, 0, 1, 2)
        field_fuzziness: Optional dict of field-specific fuzziness overrides
        field_min_scores: Optional dict of field-specific min_score thresholds

    Returns:
        UserSearchQueryBuilder instance
    """
    return UserSearchQueryBuilder(
        field_boosts=field_boosts,
        fuzziness=fuzziness,
        field_fuzziness=field_fuzziness,
        field_min_scores=field_min_scores
    )

