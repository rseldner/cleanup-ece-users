#!/usr/bin/env python3

import requests
import sys
import argparse
from typing import Dict, List, Set
from requests.auth import HTTPBasicAuth


class ElasticUserManager:
    def __init__(self, hostname: str, username: str, password: str):
        self.hostname = hostname
        self.auth = HTTPBasicAuth(username, password)

        if hostname.startswith('http://') or hostname.startswith('https://'):
            self.api_url = f"{hostname}/api/v1/users"
            self.service_accounts_url = f"{hostname}/api/v1/platform/configuration/security/service-accounts"
        elif 'localhost' in hostname or hostname.startswith('127.0.0.1'):
            self.api_url = f"http://{hostname}/api/v1/users"
            self.service_accounts_url = f"http://{hostname}/api/v1/platform/configuration/security/service-accounts"
        else:
            self.api_url = f"https://{hostname}/api/v1/users"
            self.service_accounts_url = f"https://{hostname}/api/v1/platform/configuration/security/service-accounts"

    def fetch_all_users(self, include_disabled: bool = False) -> List[Dict]:
        try:
            params = {'include_disabled': str(include_disabled).lower()}
            response = requests.get(self.api_url, auth=self.auth, params=params, verify=False)
            response.raise_for_status()

            data = response.json()
            return data.get('users', [])
        except requests.exceptions.RequestException as e:
            print(f"Error fetching users: {e}", file=sys.stderr)
            sys.exit(1)

    def fetch_service_account_users(self) -> Set[str]:
        try:
            response = requests.get(self.service_accounts_url, auth=self.auth, verify=False)
            response.raise_for_status()

            data = response.json()
            users = data.get('service_accounts', [])
            return set([user.get('user_id') for user in users])
        except requests.exceptions.RequestException as e:
            print(f"Error fetching users: {e}", file=sys.stderr)
            sys.exit(1)

    def build_creator_map(self, users: List[Dict]) -> Dict[str, List[str]]:
        creator_map = {}

        for user in users:
            username = user.get('user_name')
            metadata = user.get('metadata', {})
            created_by = metadata.get('created_by')

            if created_by and username:
                if created_by not in creator_map:
                    creator_map[created_by] = []
                creator_map[created_by].append(username)

        return creator_map

    def find_users_created_by(self, initial_creator: str, users: List[Dict]) -> Set[str]:
        creator_map = self.build_creator_map(users)
        found_users = set()
        to_process = [initial_creator]

        while to_process:
            current_creator = to_process.pop(0)
            created_users = creator_map.get(current_creator, [])

            for user in created_users:
                if user not in found_users:
                    found_users.add(user)
                    to_process.append(user)

        return found_users

    def get_user_details(self, username: str, users: List[Dict]) -> Dict:
        for user in users:
            if user.get('user_name') == username:
                return user
        return None


def main():
    parser = argparse.ArgumentParser(
        description='List all users created by a specific user and their descendants recursively',
        epilog='Example: python list_readonly_created_users.py --pipe | python delete_users.py'
    )
    parser.add_argument('--hostname', help='Elastic Cloud Enterprise hostname')
    parser.add_argument('--username', help='API username for authentication')
    parser.add_argument('--password', help='API password for authentication')
    parser.add_argument('--creator', default='readonly', help='Initial creator username to search for (default: readonly)')
    parser.add_argument('--pipe', action='store_true', help='Output only usernames (one per line) for piping to other scripts')
    parser.add_argument('--include-disabled', action='store_true', help='Include disabled users in the search')

    args = parser.parse_args()

    hostname = args.hostname or input("Enter hostname (e.g., cloud.elastic.co): ").strip()
    username = args.username or input("Enter API username: ").strip()
    password = args.password or input("Enter API password: ").strip()

    # In pipe mode, suppress informational messages (write to stderr instead)
    def info_print(message):
        if args.pipe:
            print(message, file=sys.stderr)
        else:
            print(message)

    info_print(f"\nConnecting to {hostname}...")

    manager = ElasticUserManager(hostname, username, password)

    info_print("Fetching all users...")
    users = manager.fetch_all_users(include_disabled=args.include_disabled)
    info_print(f"Found {len(users)} total users")

    info_print(f"\nFinding users created by '{args.creator}' (recursively)...")
    created_users = manager.find_users_created_by(args.creator, users)

    info_print(f"\nFinding service account users")
    service_account_users = manager.fetch_service_account_users()

    created_users.update(service_account_users)

    if not created_users:
        info_print(f"\nNo users found created by '{args.creator}' or their descendants.")
        return

    # Pipe mode: output only usernames
    if args.pipe:
        for username in sorted(created_users):
            print(username)
        return

    print(f"\nFound {len(created_users)} users created by '{args.creator}' or their descendants:\n")
    print("=" * 80)

    for username in sorted(created_users):
        user_details = manager.get_user_details(username, users)
        if user_details:
            metadata = user_details.get('metadata', {})
            security = user_details.get('security', {})

            print(f"Username: {username}")
            print(f"  Full Name: {user_details.get('full_name', 'N/A')}")
            print(f"  Email: {user_details.get('email', 'N/A')}")
            print(f"  Created By: {metadata.get('created_by', 'N/A')}")
            print(f"  Created At: {metadata.get('created_at', 'N/A')}")
            print(f"  Enabled: {security.get('enabled', 'N/A')}")
            print(f"  Builtin: {user_details.get('builtin', False)}")
            print("-" * 80)

    print(f"\nSummary:")
    print(f"  Total users to potentially delete: {len(created_users)}")
    print(f"\nUsernames only (for scripting):")
    for username in sorted(created_users):
        print(f"  - {username}")


if __name__ == "__main__":
    main()
