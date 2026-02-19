"""
Sample Python code with intentional bugs for testing CloudForge Bug Intelligence.

This file contains various types of bugs that should be detected:
- Null pointer dereferences
- SQL injection vulnerabilities
- Resource leaks
- Logic errors
- Type errors
"""

import sqlite3
import os


# BUG 1: Null pointer dereference
def process_user_data(user):
    """Process user data without null check."""
    # Missing null check - user could be None
    return user.name.upper()  # Will crash if user is None


# BUG 2: SQL injection vulnerability
def get_user_by_id(user_id):
    """Fetch user from database - VULNERABLE to SQL injection."""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # CRITICAL: SQL injection vulnerability
    query = f"SELECT * FROM users WHERE id = {user_id}"
    cursor.execute(query)
    
    result = cursor.fetchone()
    conn.close()
    return result


# BUG 3: Resource leak
def read_config_file(filename):
    """Read configuration file without proper cleanup."""
    # File handle is never closed - resource leak
    file = open(filename, 'r')
    config = file.read()
    return config  # File not closed!


# BUG 4: Division by zero
def calculate_average(numbers):
    """Calculate average without checking for empty list."""
    # Will crash if numbers is empty
    return sum(numbers) / len(numbers)


# BUG 5: Incorrect comparison
def is_admin(user_role):
    """Check if user is admin - uses assignment instead of comparison."""
    # BUG: Using = instead of ==
    if user_role = "admin":  # SyntaxError in Python, but shows intent
        return True
    return False


# BUG 6: Infinite loop potential
def wait_for_condition(check_func, timeout=10):
    """Wait for condition with potential infinite loop."""
    import time
    start = time.time()
    
    # BUG: timeout is never checked
    while not check_func():
        time.sleep(0.1)
        # Missing: if time.time() - start > timeout: break
    
    return True


# BUG 7: Race condition
shared_counter = 0

def increment_counter():
    """Increment shared counter without synchronization."""
    global shared_counter
    # BUG: Not thread-safe - race condition
    temp = shared_counter
    temp += 1
    shared_counter = temp


# BUG 8: Memory leak (Python)
class DataProcessor:
    """Data processor with circular reference."""
    
    def __init__(self):
        self.data = []
        self.parent = None
    
    def add_child(self, child):
        """Add child processor - creates circular reference."""
        self.data.append(child)
        child.parent = self  # Circular reference - potential memory leak


# BUG 9: Hardcoded credentials
def connect_to_database():
    """Connect to database with hardcoded credentials."""
    # CRITICAL: Hardcoded credentials
    username = "admin"
    password = "password123"
    host = "production-db.example.com"
    
    return f"postgresql://{username}:{password}@{host}/mydb"


# BUG 10: Path traversal vulnerability
def read_user_file(filename):
    """Read user-specified file - vulnerable to path traversal."""
    # CRITICAL: No validation - path traversal attack
    base_dir = "/var/www/uploads"
    file_path = os.path.join(base_dir, filename)
    
    with open(file_path, 'r') as f:
        return f.read()


# BUG 11: Incorrect exception handling
def parse_json_data(json_string):
    """Parse JSON with overly broad exception handling."""
    import json
    
    try:
        return json.loads(json_string)
    except:  # BUG: Bare except catches everything, even KeyboardInterrupt
        return {}


# BUG 12: Integer overflow (conceptual in Python)
def calculate_factorial(n):
    """Calculate factorial without overflow check."""
    # In languages like C/Java, this could overflow
    # In Python, it just gets very slow for large n
    if n == 0:
        return 1
    return n * calculate_factorial(n - 1)  # No recursion limit check


# BUG 13: Unvalidated redirect
def redirect_user(redirect_url):
    """Redirect user to URL without validation."""
    # SECURITY: Open redirect vulnerability
    return f"<meta http-equiv='refresh' content='0; url={redirect_url}'>"


# BUG 14: Weak cryptography
def hash_password(password):
    """Hash password using weak algorithm."""
    import hashlib
    
    # BUG: MD5 is cryptographically broken
    return hashlib.md5(password.encode()).hexdigest()


# BUG 15: Command injection
def ping_host(hostname):
    """Ping a host - vulnerable to command injection."""
    import subprocess
    
    # CRITICAL: Command injection vulnerability
    command = f"ping -c 1 {hostname}"
    result = subprocess.run(command, shell=True, capture_output=True)
    return result.stdout


# BUG 16: Missing input validation
def set_user_age(age):
    """Set user age without validation."""
    # No validation - could be negative, too large, or wrong type
    user_age = age
    return user_age


# BUG 17: Incorrect list modification during iteration
def remove_even_numbers(numbers):
    """Remove even numbers from list - modifies during iteration."""
    # BUG: Modifying list while iterating
    for num in numbers:
        if num % 2 == 0:
            numbers.remove(num)  # Skips elements!
    return numbers


# BUG 18: Missing return statement
def get_user_status(user_id):
    """Get user status - missing return in some paths."""
    if user_id > 0:
        return "active"
    elif user_id < 0:
        return "inactive"
    # BUG: No return for user_id == 0


# BUG 19: Incorrect string comparison
def check_password(password):
    """Check password strength - case-sensitive comparison issue."""
    # BUG: Should use case-insensitive comparison
    if password == "PASSWORD":
        return True
    return False


# BUG 20: Uninitialized variable
def calculate_total(items):
    """Calculate total price - uninitialized variable."""
    # BUG: total not initialized if items is empty
    for item in items:
        total += item.price  # NameError if items is empty
    return total


if __name__ == "__main__":
    print("This file contains intentional bugs for testing purposes.")
    print("Do not use this code in production!")
