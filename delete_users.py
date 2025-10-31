#!/usr/bin/env python3
import requests
import sys
import argparse
from typing import List, Tuple
from requests.auth import HTTPBasicAuth
from getpass import getpass

class ElasticUserDeleter:
    def __init__(self, hostname: str, username: str, password: str, dry_run: bool = False):
        self.hostname = hostname
        self.auth = HTTPBasicAuth(username, password)
        self.dry_run = dry_run

        if hostname.startswith('http://') or hostname.startswith('https://'):
            self.base_url = f"{hostname}/api/v1/users"
        elif 'localhost' in hostname or hostname.startswith('127.0.0.1'):
            self.base_url = f"http://{hostname}/api/v1/users"
        else:
            self.base_url = f"https://{hostname}/api/v1/users"

    def delete_user(self, user_name: str) -> Tuple[bool, str]:
        if self.dry_run:
            return True, f"DRY RUN: Would delete user '{user_name}'"

        try:
            url = f"{self.base_url}/{user_name}"
            response = requests.delete(url, auth=self.auth, verify=False)

            if response.status_code == 200:
                return True, f"Successfully deleted user '{user_name}'"
            elif response.status_code == 400:
                try:
                    error_data = response.json()
                    error_msg = error_data.get('errors', [{}])[0].get('code', 'Unknown error')
                    return False, f"Cannot delete '{user_name}': {error_msg}"
                except:
                    return False, f"Cannot delete '{user_name}': Bad request (400)"
            elif response.status_code == 404:
                return False, f"User '{user_name}' not found"
            else:
                return False, f"Failed to delete '{user_name}': HTTP {response.status_code}"

        except requests.exceptions.RequestException as e:
            return False, f"Error deleting '{user_name}': {e}"

    def delete_users_batch(self, usernames: List[str]) -> dict:
        results = {
            'successful': [],
            'failed': [],
            'total': len(usernames)
        }

        for username in usernames:
            success, message = self.delete_user(username)
            print(message)

            if success:
                results['successful'].append(username)
            else:
                results['failed'].append({'username': username, 'error': message})

        return results


def read_usernames_from_stdin() -> List[str]:
    usernames = []
    if not sys.stdin.isatty():
        for line in sys.stdin:
            line = line.strip()
            if line and not line.startswith('#'):
                if line.startswith('- '):
                    line = line[2:].strip()
                usernames.append(line)
    return usernames


def confirm_deletion(usernames: List[str], dry_run: bool) -> bool:
    if dry_run:
        print(f"\n{'='*80}")
        print("DRY RUN - No users will be deleted")
        print(f"{'='*80}\n")
        return True

    print(f"\n{'='*80}")
    print(f"WARNING: You are about to DELETE {len(usernames)} user(s)!")
    print(f"{'='*80}\n")
    print("Users to be deleted:")
    for username in usernames[:10]:
        print(f"  - {username}")
    if len(usernames) > 10:
        print(f"  ... and {len(usernames) - 10} more")

    print(f"\n{'='*80}")

    try:
        if not sys.stdin.isatty():
            with open('/dev/tty', 'r') as tty:
                print("Are you sure you want to proceed? Type 'DELETE' to confirm: ", end='', flush=True)
                response = tty.readline().strip()
        else:
            response = input("Are you sure you want to proceed? Type 'DELETE' to confirm: ")

        return response == 'DELETE'
    except (OSError, IOError):
        print("\nError: Cannot read confirmation from terminal when using piped input.")
        print("Please use --no-confirm flag to skip confirmation, or provide usernames as arguments instead of piping.")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Delete users from Elastic Cloud Enterprise API',
        epilog='Example: python list_readonly_created_users.py --pipe | python delete_users.py'
    )
    parser.add_argument('usernames', nargs='*', help='Usernames to delete (optional if using stdin)')
    parser.add_argument('--hostname', help='Elastic Cloud Enterprise hostname')
    parser.add_argument('--username', help='API username for authentication')
    parser.add_argument('--password', help='API password for authentication')
    parser.add_argument('--dry-run', action='store_true', help='Simulate deletion without actually deleting')
    parser.add_argument('--no-confirm', action='store_true', help='Skip confirmation prompt (use with caution!)')

    args = parser.parse_args()

    usernames_from_stdin = read_usernames_from_stdin()
    usernames = args.usernames if args.usernames else usernames_from_stdin

    if not usernames:
        print("Error: No usernames provided. Provide usernames as arguments or pipe them via stdin.", file=sys.stderr)
        print("\nExamples:", file=sys.stderr)
        print("  python delete_users.py user1 user2 user3", file=sys.stderr)
        print("  python list_readonly_created_users.py --pipe | python delete_users.py", file=sys.stderr)
        sys.exit(1)

    hostname = args.hostname or input("Enter hostname (e.g., cloud.elastic.co): ").strip()
    username = args.username or input("Enter API username: ").strip()
    password = args.password or getpass("Enter API password: ")

    deleter = ElasticUserDeleter(hostname, username, password, dry_run=args.dry_run)

    # Confirm deletion
    if not args.no_confirm:
        if not confirm_deletion(usernames, args.dry_run):
            print("\nDeletion cancelled by user.")
            sys.exit(0)

    # Deletions
    print(f"\n{'='*80}")
    print(f"{'DRY RUN: Simulating deletion' if args.dry_run else 'Deleting users'}...")
    print(f"{'='*80}\n")

    results = deleter.delete_users_batch(usernames)

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"Total users processed: {results['total']}")
    print(f"Successfully deleted: {len(results['successful'])}")
    print(f"Failed: {len(results['failed'])}")

    if results['failed']:
        print("\nFailed deletions:")
        for failure in results['failed']:
            print(f"  - {failure['username']}: {failure['error']}")

    if args.dry_run:
        print("\nThis was a DRY RUN. No users were actually deleted.")
        print("Remove --dry-run flag to perform actual deletions.")


if __name__ == "__main__":
    main()
