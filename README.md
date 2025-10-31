# Elastic Cloud Enterprise User Management

Scripts to manage users in Elastic Cloud Enterprise, with support for recursively finding and deleting users created by a specific user.

These scripts assume that you have the Python `requests` library installed in the environment where you run the scripts (e.g., using `pip` or within a virtual environment).

You can run these scripts from any machine — they do not need to be executed from the ECE director host.


## Usage
Before running the scripts, set the following environment variables:

`ECE_URL`: URL where ECE UI is accessible.

`ECE_ADMIN_USER_NAME`: A native ECE user with the Platform Admin role. 

`ECE_ADMIN_PASSWORD`: The password for the above user.


**Listing Users created by `readonly` user**

```bash
python list_readonly_created_users.py \
  --hostname "$ECE_URL" \
  --username "$ECE_ADMIN_USER_NAME" \
  --password "$ECE_ADMIN_PASSWORD"
```
Please read the output of the above. If there are no users to be deleted, then you don't need to run the next step. 

If there are users to be deleted, as per the output of the above step,  please execute the next step. 

**Deletion (Dry Run):**

:bulb: **Tip:** Remove `--dry-run` switch to really delete the user(s).

Using pipe:
```bash
python list_readonly_created_users.py \
  --hostname "$ECE_URL" \
  --username "$ECE_ADMIN_USER_NAME" \
  --password "$ECE_ADMIN_PASSWORD" \
  --pipe | python delete_users.py \
  --hostname "$ECE_URL" \
  --username "$ECE_ADMIN_USER_NAME" \
  --password "$ECE_ADMIN_PASSWORD" \
  --dry-run
```

Alternatively, instead of piping the output from the previous command, you can directly specify the list of users to delete:

Direct deletion:
```bash
python delete_users.py \
  --hostname "$ECE_URL" \
  --username "$ECE_ADMIN_USER_NAME" \
  --password "$ECE_ADMIN_PASSWORD" \
  --dry-run \
  user1 user2 user3
```
