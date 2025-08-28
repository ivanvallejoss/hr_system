"""
Custom exceptions for the HR System.
"""

class HRSystemError(Exception):
    """Base exception for HR System"""
    pass

class EmployeeNotFoundError(Exception):
    """Raised when employee is not found"""
    pass

class InactiveEmployeeError(Exception):
    """Raised when trying to access with inactive employee"""
    pass
class InsufficientPermissionError(Exception):
    """Raised when user doesn't have required permissions"""
    pass
class DataIntegrityError(Exception):
    """Raised when data integrity is compromised"""
    pass