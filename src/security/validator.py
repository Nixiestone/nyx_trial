"""
Input Validation & Sanitization Module
Prevents SQL Injection, XSS, Command Injection

Author: BLESSING OMOREGIE
"""

import re
from typing import Any, Optional, Tuple
from decimal import Decimal, InvalidOperation


class InputValidator:
    """
    Production-grade input validation and sanitization.
    """
    
    # Whitelisted characters for different input types
    ALPHANUMERIC_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')
    SYMBOL_PATTERN = re.compile(r'^[A-Z0-9._-]{3,20}$')
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    
    # Dangerous patterns to reject
    SQL_INJECTION_PATTERNS = [
        r"(\bOR\b.*=.*)",
        r"(\bAND\b.*=.*)",
        r"(--|#|\/\*|\*\/)",
        r"(\bDROP\b|\bDELETE\b|\bINSERT\b|\bUPDATE\b)",
        r"(\bUNION\b.*\bSELECT\b)",
        r"(;.*\bEXEC\b)",
    ]
    
    @staticmethod
    def sanitize_string(value: str, max_length: int = 255) -> str:
        """
        Sanitize string input.
        
        Args:
            value: Input string
            max_length: Maximum allowed length
            
        Returns:
            Sanitized string
            
        Raises:
            ValueError: If input is invalid
        """
        if not isinstance(value, str):
            raise ValueError("Input must be a string")
        
        # Trim whitespace
        value = value.strip()
        
        # Check length
        if len(value) > max_length:
            raise ValueError(f"Input exceeds maximum length of {max_length}")
        
        # Check for SQL injection patterns
        for pattern in InputValidator.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValueError("Potentially malicious input detected")
        
        return value
    
    @staticmethod
    def validate_telegram_chat_id(chat_id: Any) -> int:
        """
        Validate Telegram chat ID.
        
        Args:
            chat_id: Chat ID to validate
            
        Returns:
            Validated chat ID as integer
            
        Raises:
            ValueError: If invalid
        """
        try:
            chat_id_int = int(chat_id)
            
            # Telegram chat IDs are typically between -10^12 and 10^12
            if abs(chat_id_int) > 10**12:
                raise ValueError("Chat ID out of valid range")
            
            return chat_id_int
            
        except (ValueError, TypeError):
            raise ValueError(f"Invalid chat ID: {chat_id}")
    
    @staticmethod
    def validate_mt5_login(login: Any) -> int:
        """
        Validate MT5 login number.
        
        Args:
            login: MT5 login to validate
            
        Returns:
            Validated login as integer
            
        Raises:
            ValueError: If invalid
        """
        try:
            login_int = int(login)
            
            if login_int <= 0:
                raise ValueError("MT5 login must be positive")
            
            # MT5 logins are typically 6-9 digits
            if login_int > 10**10:
                raise ValueError("MT5 login out of valid range")
            
            return login_int
            
        except (ValueError, TypeError):
            raise ValueError(f"Invalid MT5 login: {login}")
    
    @staticmethod
    def validate_symbol(symbol: str) -> str:
        """
        Validate trading symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Validated symbol
            
        Raises:
            ValueError: If invalid
        """
        symbol = InputValidator.sanitize_string(symbol, max_length=20)
        
        if not InputValidator.SYMBOL_PATTERN.match(symbol):
            raise ValueError(
                f"Invalid symbol format: {symbol}. "
                "Symbols must be 3-20 uppercase alphanumeric characters."
            )
        
        return symbol
    
    @staticmethod
    def validate_lot_size(lot_size: Any) -> float:
        """
        Validate trading lot size.
        
        Args:
            lot_size: Lot size to validate
            
        Returns:
            Validated lot size
            
        Raises:
            ValueError: If invalid
        """
        try:
            lot_size_decimal = Decimal(str(lot_size))
            lot_size_float = float(lot_size_decimal)
            
            if lot_size_float <= 0:
                raise ValueError("Lot size must be positive")
            
            if lot_size_float > 1000:
                raise ValueError("Lot size unreasonably large")
            
            # Round to 2 decimal places
            return round(lot_size_float, 2)
            
        except (InvalidOperation, ValueError, TypeError):
            raise ValueError(f"Invalid lot size: {lot_size}")
    
    @staticmethod
    def validate_price(price: Any) -> float:
        """
        Validate price value.
        
        Args:
            price: Price to validate
            
        Returns:
            Validated price
            
        Raises:
            ValueError: If invalid
        """
        try:
            price_decimal = Decimal(str(price))
            price_float = float(price_decimal)
            
            if price_float <= 0:
                raise ValueError("Price must be positive")
            
            if price_float > 10**9:
                raise ValueError("Price unreasonably large")
            
            return price_float
            
        except (InvalidOperation, ValueError, TypeError):
            raise ValueError(f"Invalid price: {price}")
    
    @staticmethod
    def validate_percentage(percentage: Any, min_val: float = 0, max_val: float = 100) -> float:
        """
        Validate percentage value.
        
        Args:
            percentage: Percentage to validate
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            
        Returns:
            Validated percentage
            
        Raises:
            ValueError: If invalid
        """
        try:
            pct_float = float(percentage)
            
            if not (min_val <= pct_float <= max_val):
                raise ValueError(
                    f"Percentage must be between {min_val} and {max_val}"
                )
            
            return pct_float
            
        except (ValueError, TypeError):
            raise ValueError(f"Invalid percentage: {percentage}")
    
    @staticmethod
    def validate_account_name(name: str) -> str:
        """
        Validate account name.
        
        Args:
            name: Account name
            
        Returns:
            Validated name
            
        Raises:
            ValueError: If invalid
        """
        name = InputValidator.sanitize_string(name, max_length=50)
        
        if len(name) < 3:
            raise ValueError("Account name must be at least 3 characters")
        
        # Only allow alphanumeric, spaces, hyphens, underscores
        if not re.match(r'^[a-zA-Z0-9 _-]+$', name):
            raise ValueError(
                "Account name can only contain letters, numbers, spaces, hyphens, and underscores"
            )
        
        return name
    
    @staticmethod
    def validate_command_argument(arg: str, arg_name: str = "argument") -> str:
        """
        Validate command-line argument to prevent command injection.
        
        Args:
            arg: Argument value
            arg_name: Argument name for error messages
            
        Returns:
            Validated argument
            
        Raises:
            ValueError: If invalid
        """
        arg = InputValidator.sanitize_string(arg)
        
        # Check for shell metacharacters
        dangerous_chars = ['|', '&', ';', '$', '`', '\n', '\r', '(', ')', '<', '>']
        
        if any(char in arg for char in dangerous_chars):
            raise ValueError(
                f"Invalid {arg_name}: contains dangerous characters"
            )
        
        return arg


class RateLimiter:
    """
    Simple in-memory rate limiter for API calls and commands.
    """
    
    def __init__(self, max_calls: int = 10, time_window: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_calls: Maximum calls allowed in time window
            time_window: Time window in seconds
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = {}  # user_id -> list of timestamps
    
    def is_allowed(self, user_id: int) -> Tuple[bool, Optional[str]]:
        """
        Check if user is allowed to make a call.
        
        Args:
            user_id: User identifier
            
        Returns:
            Tuple of (is_allowed, error_message)
        """
        import time
        
        current_time = time.time()
        
        if user_id not in self.calls:
            self.calls[user_id] = []
        
        # Remove calls outside time window
        self.calls[user_id] = [
            call_time for call_time in self.calls[user_id]
            if current_time - call_time < self.time_window
        ]
        
        # Check limit
        if len(self.calls[user_id]) >= self.max_calls:
            return False, f"Rate limit exceeded. Maximum {self.max_calls} calls per {self.time_window} seconds."
        
        # Record this call
        self.calls[user_id].append(current_time)
        
        return True, None