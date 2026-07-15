"""Generate the bcrypt hash for APP_PASSWORD_HASH.

Run it, type the password twice (it does not echo), and paste the printed hash
into .env (and the VPS EnvironmentFile). The plaintext password is never stored
or written anywhere.

    python scripts/hash_password.py
"""
import getpass

import bcrypt


def main() -> None:
    password = getpass.getpass("Password: ")
    if not password:
        raise SystemExit("Password must not be empty.")
    if password != getpass.getpass("Confirm: "):
        raise SystemExit("Passwords do not match.")
    print(bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode())


if __name__ == "__main__":
    main()
