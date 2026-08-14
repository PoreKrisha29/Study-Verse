"""
Safe Deletion Script: Remove "User as admin" test account
This script safely removes the test admin user without affecting the real admin.
"""

from app import app, db, User

def delete_test_admin():
    """Safely delete the 'User as admin' test account"""
    with app.app_context():
        try:
            # Find the test user by email or name
            test_user = User.query.filter(
                db.or_(
                    User.email == 'admin@studyversefinal.com',  # Skip real admin
                    User.first_name == 'Admin User'  # This might be the test user
                )
            ).all()
            
            print("=" * 60)
            print("FOUND USERS:")
            print("=" * 60)
            for user in test_user:
                print(f"ID: {user.id}")
                print(f"Name: {user.first_name} {user.last_name}")
                print(f"Email: {user.email}")
                print(f"Is Admin: {user.is_admin}")
                print(f"Total XP: {user.total_xp}")
                print("-" * 60)
            
            # Find users with "User" in first name or "Admin User" name pattern
            test_users_to_delete = User.query.filter(
                db.and_(
                    User.email != 'admin@studyversefinal.com',  # Protect real admin
                    db.or_(
                        User.first_name == 'User',
                        User.first_name == 'Admin User',
                        User.last_name == 'as admin'
                    )
                )
            ).all()
            
            if not test_users_to_delete:
                print("\n✅ No test users found to delete.")
                print("Real admin account is safe!")
                return
            
            print("\n" + "=" * 60)
            print("USERS TO BE DELETED:")
            print("=" * 60)
            for user in test_users_to_delete:
                print(f"ID: {user.id}")
                print(f"Name: {user.first_name} {user.last_name}")
                print(f"Email: {user.email}")
                print("-" * 60)
            
            # Confirm deletion
            confirm = input("\n⚠️  Type 'DELETE' to confirm deletion: ")
            
            if confirm != 'DELETE':
                print("\n❌ Deletion cancelled.")
                return
            
            # Delete users
            for user in test_users_to_delete:
                print(f"\n🗑️  Deleting: {user.first_name} {user.last_name} ({user.email})")
                db.session.delete(user)
            
            db.session.commit()
            
            print("\n" + "=" * 60)
            print("✅ TEST USERS DELETED SUCCESSFULLY!")
            print("=" * 60)
            print(f"Deleted {len(test_users_to_delete)} test user(s)")
            print("Real admin account remains safe!")
            
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            db.session.rollback()
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    delete_test_admin()
