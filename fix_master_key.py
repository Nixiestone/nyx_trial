"""
Master Key Generator and Fixer
Run this to generate a secure master key

Author: QDev Team
Location: fix_master_key.py (CREATE IN ROOT)
"""

import secrets
import string
from pathlib import Path


def generate_secure_key(length=32):
    """Generate a cryptographically secure random key."""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def update_secrets_env():
    """Update the secrets.env file with a new master key."""
    
    secrets_path = Path('config/secrets.env')
    
    if not secrets_path.exists():
        print(f"ERROR: {secrets_path} not found!")
        print("Please create it from config/secrets.env.template first")
        return False
    
    # Read current file
    with open(secrets_path, 'r') as f:
        lines = f.readlines()
    
    # Generate new secure key
    new_key = generate_secure_key(32)
    
    # Update MASTER_KEY line
    updated_lines = []
    key_found = False
    
    for line in lines:
        if line.strip().startswith('MASTER_KEY='):
            updated_lines.append(f'MASTER_KEY={new_key}\n')
            key_found = True
            print(f"\n✓ Updated MASTER_KEY in {secrets_path}")
        else:
            updated_lines.append(line)
    
    # If MASTER_KEY not found, add it
    if not key_found:
        updated_lines.append(f'\nMASTER_KEY={new_key}\n')
        print(f"\n✓ Added MASTER_KEY to {secrets_path}")
    
    # Write back
    with open(secrets_path, 'w') as f:
        f.writelines(updated_lines)
    
    print(f"\nYour new MASTER_KEY: {new_key}")
    print(f"Length: {len(new_key)} characters")
    print("\n⚠️  IMPORTANT: Keep this key secret!")
    print("⚠️  DO NOT commit secrets.env to GitHub!")
    
    return True


def main():
    print("=" * 70)
    print("MASTER KEY GENERATOR")
    print("=" * 70)
    
    print("\nThis will generate a secure 32-character master key")
    print("for encrypting your MT5 credentials.")
    
    response = input("\nContinue? (y/n): ")
    
    if response.lower() != 'y':
        print("Cancelled.")
        return
    
    if update_secrets_env():
        print("\n" + "=" * 70)
        print("✓ MASTER_KEY successfully updated!")
        print("=" * 70)
        print("\nYou can now run: python main.py")
    else:
        print("\n❌ Failed to update MASTER_KEY")


if __name__ == "__main__":
    main()