"""
User Type Enumeration

Defines the valid user types for the ITSM system.
"""

from enum import Enum


class UserType(str, Enum):
    """
    Valid user types in the ITSM system.
    
    Attributes:
        REQUESTER: End users who submit requests
        TECHNICIAN: IT staff who handle and resolve requests
    """
    REQUESTER = "requester"
    TECHNICIAN = "technician"

