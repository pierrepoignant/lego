# User Authentication System

This document describes the user authentication and management system for the LEGO Brand Manager application.

## Features

- **Database-backed user authentication** - Users are stored in the database with hashed passwords
- **Password security** - Passwords are hashed using Werkzeug's secure password hashing
- **Role-based access control** - Admin and regular user roles
- **User management** - Admin users can create, edit, and delete users
- **Backward compatibility** - Still supports config.ini authentication as fallback

## Database Schema

### Users Table

```sql
CREATE TABLE `users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(255) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `email` varchar(255) DEFAULT NULL,
  `is_admin` tinyint(1) NOT NULL DEFAULT '0',
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `last_login` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
);
```

## Setup Instructions

### Step 1: Run Database Migration

Create the users table:

```bash
mysql -h 127.0.0.1 -u root -p lego < database/create_users_table.sql
```

### Step 2: Create Initial Admin User

Create your first admin user:

```bash
python3 database/create_initial_admin.py admin yourpassword admin@example.com
```

Replace:
- `admin` with your desired username
- `yourpassword` with your desired password (minimum 6 characters)
- `admin@example.com` with your email (optional)

### Step 3: Restart Flask App

Restart your Flask application to load the new authentication system:

```bash
python3 flask_app.py
```

## Usage

### Logging In

1. Navigate to the login page
2. Enter your username and password
3. The system will check the database first, then fall back to config.ini if no users exist

### User Management (Admin Only)

Admin users can access the user management page from the navigation menu:

1. Click **"👥 Users"** in the Stats dropdown (admin only)
2. View all users, their roles, and status
3. Add new users with the **"➕ Add User"** button
4. Edit users by clicking **"Edit"** on any user row
5. Delete users (cannot delete your own account)

### Creating Users

**Via Web Interface (Admin):**
1. Go to Users page
2. Click "Add User"
3. Fill in username, password (min 6 chars), email (optional)
4. Check "Admin User" if you want admin privileges
5. Click "Create User"

**Via Script:**
```bash
python3 database/create_initial_admin.py username password email@example.com
```

### Editing Users

1. Go to Users page
2. Click "Edit" on the user you want to modify
3. Update fields as needed
4. Leave password blank to keep current password
5. Click "Update User"

### User Roles

- **Admin Users**: Can access all features including user management
- **Regular Users**: Can access all features except user management

### User Status

- **Active**: User can log in
- **Inactive**: User cannot log in (account disabled)

## Security Features

- **Password Hashing**: All passwords are hashed using Werkzeug's secure password hashing (PBKDF2)
- **Session Management**: User sessions track login status and admin privileges
- **Access Control**: Admin-only routes are protected with `@admin_required` decorator
- **Self-Protection**: Users cannot delete their own accounts

## API Functions

### Authentication Functions

- `verify_user(username, password)` - Verify user credentials
- `create_user(username, password, email, is_admin)` - Create a new user
- `login_required` - Decorator for routes requiring login
- `admin_required` - Decorator for routes requiring admin access

### Routes

- `/login` - Login page
- `/logout` - Logout (clears session)
- `/users` - List all users (admin only)
- `/users/add` - Add new user (admin only)
- `/users/edit/<user_id>` - Edit user (admin only)
- `/users/delete/<user_id>` - Delete user (admin only)

## Backward Compatibility

The system maintains backward compatibility with the old config.ini authentication:

1. First checks database for user
2. If not found, falls back to config.ini credentials
3. This allows gradual migration from config.ini to database users

## Troubleshooting

### "No users found" after migration

Run the create_initial_admin.py script to create your first user.

### Cannot access user management

Only admin users can access user management. Make sure your user has `is_admin = 1` in the database.

### Password too short

Passwords must be at least 6 characters long.

### User already exists

Usernames must be unique. Choose a different username or edit the existing user.

## Migration from Config.ini

To migrate from config.ini to database users:

1. Run the database migration
2. Create an admin user with the same username/password as in config.ini
3. Test login with the new user
4. Once confirmed working, you can remove the auth section from config.ini (optional)

