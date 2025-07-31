from flask import Flask, render_template, send_from_directory, request, redirect, url_for, session, jsonify
from werkzeug.utils import secure_filename
import os
import json
import glob
import socket
import re
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'change-this-secret'

# Global client service queue (in production, use Redis or database)
CLIENT_SERVICE_QUEUE = {}

# Import and register the account blueprint
from account_routes import account_bp
app.register_blueprint(account_bp)

# Initialize database on startup
try:
    from database_init import init_database
    print("Initializing database...")
    init_database()
except Exception as e:
    print(f"Database initialization error: {e}")
    print("Continuing without database initialization...")

RESOURCE_EXTENSIONS = {'.pdf', '.zip', '.rar', '.7z'}
POSTS_PATH = os.path.join(app.root_path, 'posts.json')
CATEGORIES_PATH = os.path.join(app.root_path, 'categories.json')
ADMIN_PASSWORD = os.environ.get('TRUCKSOFT_ADMIN_PASSWORD', 'secret')
UPLOAD_FOLDER = os.path.join(app.root_path, 'uploads')
CHATS_PATH = os.path.join(app.root_path, 'chat.json')
ADMINS_PATH = os.path.join(app.root_path, 'admins.json')
EXTERNAL_TOOLS_CONFIG_PATH = os.path.join(app.root_path, 'external_tools_config.json')
ALLOWED_ATTACH_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'tiff', 'svg', 'txt', 'doc', 'docx', 'zip', 'rar', '7z'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def cleanup_chat_on_startup():
    """Clear chat data and remove chat-related uploaded images on application startup"""
    try:
        # Load existing chats to get image filenames before clearing
        chat_images = []
        if os.path.exists(CHATS_PATH):
            with open(CHATS_PATH, 'r', encoding='utf-8') as f:
                chats = json.load(f)
                for chat in chats:
                    if chat.get('image'):
                        chat_images.append(chat['image'])
        
        # Clear the chat.json file
        with open(CHATS_PATH, 'w', encoding='utf-8') as f:
            json.dump([], f, indent=2, ensure_ascii=False)
        
        # Remove chat image files from uploads folder
        for image_name in chat_images:
            image_path = os.path.join(UPLOAD_FOLDER, image_name)
            if os.path.exists(image_path):
                try:
                    os.remove(image_path)
                    print(f"Removed chat image: {image_name}")
                except OSError as e:
                    print(f"Error removing chat image {image_name}: {e}")
        
        # Also remove any orphaned image files that might be chat images
        # (files that start with timestamp pattern and have image extensions)
        image_extensions = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'tiff', 'svg'}
        for ext in image_extensions:
            pattern = os.path.join(UPLOAD_FOLDER, f'????????_*.{ext}')
            for file_path in glob.glob(pattern):
                # Only remove if it looks like a chat image (timestamp_filename pattern)
                filename = os.path.basename(file_path)
                if len(filename) >= 15 and filename[8] == '_' and filename[:8].isdigit():
                    try:
                        os.remove(file_path)
                        print(f"Removed orphaned chat image: {filename}")
                    except OSError as e:
                        print(f"Error removing orphaned image {filename}: {e}")
        
        print("Chat cleanup completed successfully")
        
    except Exception as e:
        print(f"Error during chat cleanup: {e}")


# Clean up chat data on startup
cleanup_chat_on_startup()


def load_posts():
    if not os.path.exists(POSTS_PATH):
        return []
    with open(POSTS_PATH, 'r', encoding='utf-8') as f:
        posts = json.load(f)
        for p in posts:
            p.setdefault('embedded', [])
            p.setdefault('tags', [])  # Ensure tags field always exists
        return posts


def save_posts(posts):
    with open(POSTS_PATH, 'w', encoding='utf-8') as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)


def load_categories():
    if not os.path.exists(CATEGORIES_PATH):
        return ['General']
    with open(CATEGORIES_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_categories(categories):
    with open(CATEGORIES_PATH, 'w', encoding='utf-8') as f:
        json.dump(categories, f, indent=2, ensure_ascii=False)


RESOURCES_PATH = os.path.join(app.root_path, "resources.json")


def load_resources():
    if not os.path.exists(RESOURCES_PATH):
        return []
    with open(RESOURCES_PATH, "r", encoding='utf-8') as f:
        resources = json.load(f)
        # Ensure backwards compatibility - add category field if missing
        for resource in resources:
            resource.setdefault('category', 'General')
        return resources


def save_resources(resources):
    with open(RESOURCES_PATH, "w", encoding='utf-8') as f:
        json.dump(resources, f, indent=2, ensure_ascii=False)


def load_chats():
    if not os.path.exists(CHATS_PATH):
        return []
    with open(CHATS_PATH, "r", encoding='utf-8') as f:
        return json.load(f)


def save_chats(chats):
    with open(CHATS_PATH, "w", encoding='utf-8') as f:
        json.dump(chats, f, indent=2, ensure_ascii=False)


def load_admins():
    if not os.path.exists(ADMINS_PATH):
        return []
    with open(ADMINS_PATH, "r", encoding='utf-8') as f:
        return json.load(f)


def save_admins(admins):
    with open(ADMINS_PATH, "w", encoding='utf-8') as f:
        json.dump(admins, f, indent=2, ensure_ascii=False)


def load_external_tools_config():
    """Load external tools configuration."""
    if not os.path.exists(EXTERNAL_TOOLS_CONFIG_PATH):
        # Return default config if file doesn't exist
        return {
            "server_tools": [],
            "settings": {
                "allow_custom_tools": True,
                "allow_user_tools": True,
                "require_admin_approval": False,
                "log_tool_usage": True,
                "max_user_tools": 10
            }
        }
    
    try:
        with open(EXTERNAL_TOOLS_CONFIG_PATH, "r", encoding='utf-8') as f:
            config = json.load(f)
            
            # Handle legacy format
            if "tools" in config and "server_tools" not in config:
                config["server_tools"] = config.pop("tools", [])
            
            # Ensure server_tools exists
            if "server_tools" not in config:
                config["server_tools"] = []
                
            return config
    except Exception as e:
        print(f"Error loading external tools config: {e}")
        return {"server_tools": [], "settings": {}}


def save_external_tools_config(config):
    """Save external tools configuration."""
    try:
        with open(EXTERNAL_TOOLS_CONFIG_PATH, "w", encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving external tools config: {e}")
        return False



def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_ATTACH_EXTENSIONS


def clean_content(content):
    """Clean content to remove unwanted characters that might be introduced"""
    if not content:
        return content
    
    # Remove any standalone lowercase 'a' characters that appear on their own lines
    import re
    # Pattern to match lines that only contain 'a' (with optional whitespace)
    content = re.sub(r'\n\s*a\s*\n', '\n\n', content)
    # Pattern to match 'a' at the start of lines followed by whitespace
    content = re.sub(r'\na\s*\n', '\n\n', content)
    # Remove multiple consecutive newlines (more than 2)
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    return content.strip()


def save_uploaded_files(files):
    saved = []
    for f in files:
        if f and allowed_file(f.filename):
            name = datetime.utcnow().strftime('%Y%m%d%H%M%S_') + secure_filename(f.filename)
            path = os.path.join(UPLOAD_FOLDER, name)
            f.save(path)
            saved.append(name)
    return saved


@app.route('/')
def index():
    resources = load_resources()
    categories = load_categories()
    
    # Organize resources by category
    resources_by_category = {}
    for resource in resources:
        category = resource.get('category', 'General')
        if category not in resources_by_category:
            resources_by_category[category] = []
        resources_by_category[category].append(resource)
    
    # Ensure all categories exist in the dict (even if empty)
    for category in categories:
        if category not in resources_by_category:
            resources_by_category[category] = []
    
    return render_template('index.html', resources=resources, resources_by_category=resources_by_category, categories=categories)


@app.route('/howto')
def forum():
    original_posts = load_posts()
    categories = load_categories()
    resources = load_resources()
    
    # Get pagination and sorting parameters
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    sort_by = request.args.get('sort_by', 'newest')  # newest, oldest, title
    category_filter = request.args.get('category', 'all')
    search_query = request.args.get('search', '').strip().lower()
    tag_filters = request.args.get('tags', '').strip()
    
    # Organize resources by category
    resources_by_category = {}
    for resource in resources:
        category = resource.get('category', 'General')
        if category not in resources_by_category:
            resources_by_category[category] = []
        resources_by_category[category].append(resource)
    
    # Get resources for the selected category
    category_resources = []
    if category_filter != 'all' and category_filter in categories:
        category_resources = resources_by_category.get(category_filter, [])
    else:
        # If viewing all posts, show only General category resources
        category_resources = resources_by_category.get('General', [])
    
    # Add default values and create posts with original indices
    posts_with_indices = []
    for original_idx, p in enumerate(original_posts):
        p.setdefault('category', 'General')
        p.setdefault('created', datetime.utcnow().strftime('%Y-%m-%d %H:%M'))
        p.setdefault('tags', [])  # Ensure tags field exists
        posts_with_indices.append({'original_idx': original_idx, 'post': p})
    
    tags = sorted({t for item in posts_with_indices for t in item['post'].get('tags', [])})
    
    # Add "All Posts" as the first category
    all_categories = ['All Posts'] + categories
    
    # Sort posts based on sort_by parameter
    if sort_by == 'oldest':
        posts_with_indices.sort(key=lambda x: x['post'].get('created', ''))
    elif sort_by == 'title':
        posts_with_indices.sort(key=lambda x: x['post'].get('title', '').lower())
    else:  # newest (default)
        posts_with_indices.sort(key=lambda x: x['post'].get('created', ''), reverse=True)
    
    # Filter posts by category if not "all"
    if category_filter != 'all' and category_filter in categories:
        filtered_posts = [item for item in posts_with_indices if item['post'].get('category', 'General') == category_filter]
    else:
        filtered_posts = posts_with_indices
    
    # Apply search filter if provided
    if search_query:
        search_filtered = []
        for item in filtered_posts:
            post = item['post']
            # Search in title and content
            title_match = search_query in post.get('title', '').lower()
            content_match = search_query in post.get('content', '').lower()
            if title_match or content_match:
                search_filtered.append(item)
        filtered_posts = search_filtered
    
    # Apply tag filters if provided
    if tag_filters:
        tag_list = [tag.strip() for tag in tag_filters.split(',') if tag.strip()]
        if tag_list:
            tag_filtered = []
            for item in filtered_posts:
                post_tags = item['post'].get('tags', [])
                # Check if all selected tags are in the post's tags
                if all(tag in post_tags for tag in tag_list):
                    tag_filtered.append(item)
            filtered_posts = tag_filtered
    
    # Calculate pagination
    total_posts = len(filtered_posts)
    total_pages = (total_posts + per_page - 1) // per_page
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_posts = filtered_posts[start_idx:end_idx]
    
    # Build posts by category structure
    posts_by_cat = {c: [] for c in all_categories}
    
    # Add all posts to "All Posts" category (paginated)
    for item in paginated_posts:
        posts_by_cat['All Posts'].append({'index': item['original_idx'], 'post': item['post']})
    
    # Add posts to their specific categories (not paginated for category tabs)
    for item in posts_with_indices:
        cat = item['post'].get('category', 'General')
        posts_by_cat.setdefault(cat, []).append({'index': item['original_idx'], 'post': item['post']})
    
    # Pagination info
    pagination = {
        'page': page,
        'per_page': per_page,
        'total_pages': total_pages,
        'total_posts': total_posts,
        'has_prev': page > 1,
        'has_next': page < total_pages,
            'prev_num': page - 1 if page > 1 else None,
            'next_num': page + 1 if page < total_pages else None
    }

    return render_template(
        'forum.html',
        categories=all_categories,
        tags=tags,
        posts_by_cat=posts_by_cat,
        pagination=pagination,
        sort_by=sort_by,
        category_filter=category_filter,
        per_page=per_page,
        search_query=search_query,
        tag_filters=tag_filters,
        category_resources=category_resources,
        resources_by_category=resources_by_category
    )


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            error = 'Username and password are required'
            return render_template('login.html', error=error)
        
        # Check master admin password first
        if password == ADMIN_PASSWORD:
            session['logged_in'] = True
            session['secret_admin'] = True
            session['username'] = username or 'admin'
            session['first'] = ''
            session['last'] = ''
            print(f"Admin login successful for: {username}")
            return redirect(url_for('new_post'))
        
        # Check SQLite database users
        try:
            from db_utils import authenticate_user
            
            success, user_data = authenticate_user(username, password)
            
            if success and user_data:
                session['logged_in'] = True
                session['secret_admin'] = False
                session['username'] = username
                session['first'] = user_data.get('first_name', '') or ''
                session['last'] = user_data.get('last_name', '') or ''
                
                print(f"Database login successful for: {username}")
                return redirect(url_for('new_post'))
            
        except Exception as e:
            print(f"Database login error: {e}")
        
        # Fallback to JSON-based admins (for backwards compatibility)
        try:
            admins = load_admins()
            for a in admins:
                if a.get('username') == username and a.get('password') == password:
                    session['logged_in'] = True
                    session['secret_admin'] = False
                    session['username'] = username
                    session['first'] = a.get('first', '')
                    session['last'] = a.get('last', '')
                    print(f"JSON admin login successful for: {username}")
                    return redirect(url_for('new_post'))
        except Exception as e:
            print(f"JSON admin login error: {e}")
        
        error = 'Invalid username or password'
        print(f"Login failed for username: {username}")
        
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('secret_admin', None)
    session.pop('username', None)
    session.pop('first', None)
    session.pop('last', None)
    return redirect(url_for('forum'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        first = request.form.get('first', '').strip()
        last = request.form.get('last', '').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        # Validate input
        if not all([first, last, username, password]):
            error = 'All fields are required'
        elif len(username) < 3:
            error = 'Username must be at least 3 characters long'
        elif len(password) < 6:
            error = 'Password must be at least 6 characters long'
        else:
            # Import database utilities
            from db_utils import create_user
            
            # Generate email
            email = f"{username}@techguides.local"
            
            # Attempt to create user
            success, message = create_user(
                username=username,
                email=email,
                password=password,
                first_name=first,
                last_name=last,
                external_features=0  # Default to disabled
            )
            
            if success:
                print(f"Registration successful for user: {username}")
                return redirect(url_for('login'))
            else:
                error = message
                print(f"Registration failed for user {username}: {message}")
                
    return render_template('register.html', error=error)


@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    chats = load_chats()
    if request.method == 'POST':
        text = request.form.get('text', '').strip()
        image_file = request.files.get('image')
        image_name = ''
        if image_file and image_file.filename:
            allowed = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'tiff', 'svg'}
            ext = image_file.filename.rsplit('.', 1)[-1].lower() if '.' in image_file.filename else ''
            if ext in allowed:
                name = datetime.utcnow().strftime('%Y%m%d%H%M%S_') + secure_filename(image_file.filename)
                path = os.path.join(UPLOAD_FOLDER, name)
                image_file.save(path)
                image_name = name
        if text or image_name:
            name = (f"{session.get('first','')} {session.get('last','')}").strip() or session.get('username', 'Admin')
            chats.append({
                'name': name,
                'text': text,
                'image': image_name,
                'created': datetime.utcnow().strftime('%Y-%m-%d %H:%M')
            })
            save_chats(chats)
            return redirect(url_for('chat'))
    return render_template('chat.html', messages=chats)


@app.route('/chat-data')
def chat_data():
    if not session.get('logged_in'):
        return jsonify({'error': 'unauthorized'}), 401
    return jsonify({'messages': load_chats()})


@app.route('/manage-admins', methods=['GET', 'POST'])
def manage_admins():
    if not session.get('logged_in') or not session.get('secret_admin'):
        return redirect(url_for('login'))
    
    error = None
    success = None
    
    if request.method == 'POST':
        action = request.form.get('action', '')
        username = request.form.get('username', '').strip()
        
        if action == 'delete' and username:
            try:
                from db_utils import delete_user
                success_flag, message = delete_user(username)
                if success_flag:
                    success = message
                else:
                    error = message
            except Exception as e:
                error = f"Error deleting user: {str(e)}"
                
        elif action == 'delete_legacy' and username:
            try:
                legacy_admins = load_admins()
                legacy_admins = [a for a in legacy_admins if a.get('username') != username]
                save_admins(legacy_admins)
                success = f"Legacy admin {username} removed"
            except Exception as e:
                error = f"Error removing legacy admin: {str(e)}"
                
        elif action == 'toggle_external' and username:
            try:
                from db_utils import toggle_user_external_features
                success_flag, message = toggle_user_external_features(username)
                if success_flag:
                    success = message
                else:
                    error = message
            except Exception as e:
                error = f"Error updating user: {str(e)}"
        
        return redirect(url_for('manage_admins'))
    
    # Load users from database
    try:
        from db_utils import get_all_users
        admins = get_all_users()
    except Exception as e:
        print(f"Error loading users: {e}")
        admins = []
        error = "Error loading users from database"
    
    # Also load legacy JSON admins for backwards compatibility
    legacy_admins = load_admins()
    
    return render_template('manage_admins.html', 
                         admins=admins, 
                         legacy_admins=legacy_admins,
                         error=error, 
                         success=success)


@app.route('/categories', methods=['GET', 'POST'])
def manage_categories():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    categories = load_categories()
    error = None
    if request.method == 'POST':
        action = request.form.get('action', 'add')
        if action == 'add':
            new_cat = request.form.get('category', '').strip()
            if new_cat and new_cat not in categories:
                categories.append(new_cat)
                save_categories(categories)
            else:
                error = 'Invalid or duplicate category'
        elif action == 'edit':
            old = request.form.get('old', '')
            new = request.form.get('new', '').strip()
            if old in categories and new and new not in categories:
                posts = load_posts()
                for p in posts:
                    if p.get('category') == old:
                        p['category'] = new
                save_posts(posts)
                
                # Also update resources with the old category
                resources = load_resources()
                for r in resources:
                    if r.get('category') == old:
                        r['category'] = new
                save_resources(resources)
                
                categories[categories.index(old)] = new
                save_categories(categories)
            else:
                error = 'Invalid category name'
        elif action == 'delete':
            name = request.form.get('name', '')
            if name in categories and name != 'General':
                posts = load_posts()
                for p in posts:
                    if p.get('category') == name:
                        p['category'] = 'General'
                save_posts(posts)
                
                # Also move resources from deleted category to General
                resources = load_resources()
                for r in resources:
                    if r.get('category') == name:
                        r['category'] = 'General'
                save_resources(resources)
                
                categories.remove(name)
                save_categories(categories)
            else:
                error = 'Cannot delete category'
    return render_template('categories.html', categories=categories, error=error)


@app.route('/resources-admin', methods=['GET', 'POST'])
def manage_resources():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    resources = load_resources()
    error = None
    if request.method == 'POST':
        action = request.form.get('action', 'add')
        if action == 'add':
            title = request.form.get('title', '').strip()
            desc = request.form.get('description', '').strip()
            rtype = request.form.get('type', 'download')
            category = request.form.get('category', 'General').strip()
            dynamic = bool(request.form.get('dynamic'))
            path = ''
            if rtype == 'download':
                file = request.files.get('file')
                if not file or file.filename == '':
                    error = 'File required'
                else:
                    fname = secure_filename(file.filename or '')
                    file.save(os.path.join(app.root_path, fname))
                    path = fname
            elif rtype == 'url':
                path = request.form.get('url', '').strip()
                if not path:
                    error = 'URL required'
            elif rtype == 'file_explorer':
                path = request.form.get('file_path', '').strip()
                if not path:
                    error = 'File path required'
                # Validate that it's a file:// URL or convert local path to file:// URL
                elif not path.startswith('file://'):
                    # Convert Windows path to file:// URL if needed
                    if path.startswith('\\\\'):
                        # UNC path - format: \\server\share becomes file://server/share
                        path = 'file://' + path.replace('\\', '/')[2:]
                    elif len(path) > 1 and path[1] == ':':
                        # Drive letter path - format: C:\folder becomes file:///C:/folder
                        path = 'file:///' + path.replace('\\', '/')
                    else:
                        error = 'File path must be a valid local path or file:// URL'
            if not error and title:
                resources.append({'title': title, 'description': desc, 'type': rtype, 'path': path, 'dynamic': dynamic, 'category': category})
                save_resources(resources)
                return redirect(url_for('manage_resources'))
            elif not title:
                error = 'Title required'
        elif action == 'delete':
            idx = int(request.form.get('index', -1))
            if 0 <= idx < len(resources):
                resources.pop(idx)
                save_resources(resources)
                return redirect(url_for('manage_resources'))
        elif action == 'edit':
            idx = int(request.form.get('index', -1))
            if 0 <= idx < len(resources):
                title = request.form.get('title', '').strip()
                desc = request.form.get('description', '').strip()
                category = request.form.get('category', 'General').strip()
                if title:
                    resources[idx]['title'] = title
                    resources[idx]['description'] = desc
                    resources[idx]['category'] = category
                    save_resources(resources)
                    return redirect(url_for('manage_resources'))
                else:
                    error = 'Title required'
    
    # Load custom data tables for reference
    try:
        from db_utils import get_custom_tables
        custom_tables = get_custom_tables()
    except Exception as e:
        print(f"Error loading custom tables for resources: {e}")
        custom_tables = []
    
    return render_template('resources_admin.html', 
                         resources=resources, 
                         categories=load_categories(), 
                         custom_tables=custom_tables,
                         error=error)


@app.route('/new', methods=['GET', 'POST'])
def new_post():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    if request.method == 'POST':
        posts = load_posts()
        attachments = save_uploaded_files(request.files.getlist('attachments'))
        embedded = [f for f in request.form.get('embedded_images', '').split(',') if f]
        tags = [t.strip() for t in request.form.get('tags', '').split(',') if t.strip()]
        
        # Clean the content to remove unwanted characters
        content = clean_content(request.form['content'])
        
        posts.insert(0, {
            'title': request.form['title'].strip(),
            'content': content,
            'author': 'Admin',
            'created': datetime.utcnow().strftime('%Y-%m-%d %H:%M'),
            'attachments': attachments,
            'embedded': embedded,
            'locked': False,
            'category': request.form['category'],
            'tags': tags
        })
        save_posts(posts)
        return redirect(url_for('forum'))
    categories = load_categories()
    return render_template('newpost.html', post=None, categories=categories)


@app.route('/tag-manager-html')
def tag_manager_html():
    """Return HTML template code for the tag manager"""
    html_code = '''
<!-- Replace your existing tags input field with this tag manager -->
<div class="form-group">
    <label for="tag-manager">Tags:</label>
    <div id="tag-container" style="min-height: 40px; border: 1px solid #ccc; padding: 8px; border-radius: 4px; margin-bottom: 8px;">
        <!-- Tags will be displayed here -->
    </div>
    <div style="display: flex; gap: 8px;">
        <input type="text" id="new-tag-input" placeholder="Enter new tag..." style="flex: 1; padding: 4px;">
        <button type="button" id="add-tag-btn" style="padding: 4px 12px;">Add Tag</button>
    </div>
</div>

<!-- Include the JavaScript -->
<script src="/tag-manager-js"></script>
<script>
    // Initialize the tag manager when the page loads
    document.addEventListener('DOMContentLoaded', function() {
        // Replace POST_INDEX with the actual post index
        initTagManager({{ index if index is defined else 0 }});
    });
</script>

<!-- Keep the original tags input hidden for backwards compatibility -->
<input type="hidden" name="tags" id="tags-hidden" value="{{ post.tags|join(',') if post else '' }}">
'''
    
    response = app.response_class(
        response=html_code,
        status=200,
        mimetype='text/html'
    )
    return response


@app.route('/tag-manager-js')
def tag_manager_js():
    """Return JavaScript code for the tag manager"""
    js_code = '''
function initTagManager(postIndex) {
    const tagContainer = document.getElementById('tag-container');
    const addTagBtn = document.getElementById('add-tag-btn');
    const newTagInput = document.getElementById('new-tag-input');
    
    if (!tagContainer || !addTagBtn || !newTagInput) {
        console.error('Tag manager elements not found');
        return;
    }
    
    // Load existing tags
    loadTags();
    
    function loadTags() {
        fetch(`/post-tags/${postIndex}`)
            .then(response => response.json())
            .then(data => {
                if (data.tags) {
                    displayTags(data.tags);
                }
            })
            .catch(error => console.error('Error loading tags:', error));
    }
    
    function displayTags(tags) {
        tagContainer.innerHTML = '';
        if (tags.length === 0) {
            tagContainer.innerHTML = '<span class="text-muted">No tags yet</span>';
            return;
        }
        
        tags.forEach(tag => {
            const tagElement = createTagElement(tag);
            tagContainer.appendChild(tagElement);
        });
    }
    
    function createTagElement(tag) {
        const tagSpan = document.createElement('span');
        tagSpan.className = 'badge bg-secondary me-2 mb-2 d-inline-flex align-items-center';
        tagSpan.style.fontSize = '0.85em';
        
        const tagText = document.createElement('span');
        tagText.textContent = tag;
        tagText.className = 'me-2';
        
        const removeBtn = document.createElement('button');
        removeBtn.innerHTML = '&times;';
        removeBtn.className = 'btn-close btn-close-white';
        removeBtn.style.cssText = 'font-size: 0.75em; padding: 0; margin: 0; width: 12px; height: 12px;';
        removeBtn.onclick = (e) => {
            e.preventDefault();
            removeTag(tag);
        };
        
        tagSpan.appendChild(tagText);
        tagSpan.appendChild(removeBtn);
        return tagSpan;
    }
    
    function addTag() {
        const tag = newTagInput.value.trim();
        if (!tag) return;
        
        fetch(`/post-tags/${postIndex}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tag: tag })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayTags(data.tags);
                newTagInput.value = '';
            } else {
                alert(data.error || 'Error adding tag');
            }
        })
        .catch(error => {
            console.error('Error adding tag:', error);
            alert('Error adding tag');
        });
    }
    
    function removeTag(tag) {
        fetch(`/post-tags/${postIndex}`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tag: tag })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayTags(data.tags);
            } else {
                alert(data.error || 'Error removing tag');
            }
        })
        .catch(error => {
            console.error('Error removing tag:', error);
            alert('Error removing tag');
        });
    }
    
    // Event listeners
    addTagBtn.onclick = (e) => {
        e.preventDefault();
        addTag();
    };
    
    newTagInput.onkeypress = function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            addTag();
        }
    };
    
    console.log('Tag manager initialized for post', postIndex);
}
'''
    
    response = app.response_class(
        response=js_code,
        status=200,
        mimetype='application/javascript'
    )
    return response


@app.route('/post-tags/<int:index>', methods=['GET', 'POST', 'DELETE'])
def manage_post_tags(index):
    """API endpoint for managing tags on a specific post"""
    if not session.get('logged_in'):
        return jsonify({'error': 'Not authenticated'}), 401
    
    posts = load_posts()
    if index < 0 or index >= len(posts):
        return jsonify({'error': 'Post not found'}), 404
    
    post = posts[index]
    
    if request.method == 'GET':
        # Return current tags
        return jsonify({
            'tags': post.get('tags', []),
            'post_title': post.get('title', 'Untitled')
        })
    
    elif request.method == 'POST':
        # Add a new tag or set all tags
        data = request.get_json() or {}
        
        if 'tag' in data:
            # Add a single tag
            new_tag = data['tag'].strip()
            if new_tag and new_tag not in post.get('tags', []):
                post.setdefault('tags', []).append(new_tag)
                save_posts(posts)
                return jsonify({'success': True, 'tags': post['tags']})
            else:
                return jsonify({'error': 'Tag already exists or is empty'}), 400
        
        elif 'tags' in data:
            # Set all tags (replace existing)
            new_tags = [tag.strip() for tag in data['tags'] if tag.strip()]
            post['tags'] = new_tags
            save_posts(posts)
            return jsonify({'success': True, 'tags': post['tags']})
        
        else:
            return jsonify({'error': 'No tag data provided'}), 400
    
    elif request.method == 'DELETE':
        # Remove a specific tag
        data = request.get_json() or {}
        tag_to_remove = data.get('tag', '').strip()
        
        if tag_to_remove and tag_to_remove in post.get('tags', []):
            post['tags'].remove(tag_to_remove)
            save_posts(posts)
            return jsonify({'success': True, 'tags': post['tags']})
        else:
            return jsonify({'error': 'Tag not found'}), 404
    
    # This should never be reached, but just in case
    return jsonify({'error': 'Invalid request method'}), 405


@app.route('/debug-tags/<int:index>')
def debug_tags(index):
    """Debug route to inspect tag data for a specific post"""
    if not session.get('logged_in') or not session.get('secret_admin'):
        return {'error': 'unauthorized'}, 401
    
    posts = load_posts()
    if index < 0 or index >= len(posts):
        return {'error': 'Post not found'}, 404
    
    post = posts[index]
    return {
        'index': index,
        'title': post.get('title', 'No title'),
        'tags': post.get('tags', []),
        'tags_type': str(type(post.get('tags', []))),
        'has_tags_field': 'tags' in post,
        'all_fields': list(post.keys())
    }


@app.route('/api/resources')
def api_resources():
    """API endpoint to get all resources organized by category"""
    resources = load_resources()
    categories = load_categories()
    
    # Organize resources by category
    resources_by_category = {}
    for resource in resources:
        category = resource.get('category', 'General')
        if category not in resources_by_category:
            resources_by_category[category] = []
        resources_by_category[category].append(resource)
    
    return jsonify({
        'resources': resources,
        'resources_by_category': resources_by_category,
        'categories': categories
    })


@app.route('/api/resources/<category>')
def api_resources_by_category(category):
    """API endpoint to get resources for a specific category"""
    resources = load_resources()
    category_resources = [r for r in resources if r.get('category', 'General') == category]
    
    return jsonify({
        'category': category,
        'resources': category_resources,
        'count': len(category_resources)
    })


@app.route('/cleanup-resources', methods=['POST'])
def cleanup_resources():
    """Admin route to add category field to existing resources"""
    if not session.get('logged_in') or not session.get('secret_admin'):
        return redirect(url_for('login'))
    
    resources = load_resources()
    updated_count = 0
    
    for resource in resources:
        if 'category' not in resource:
            resource['category'] = 'General'
            updated_count += 1
    
    if updated_count > 0:
        save_resources(resources)
    
    return {
        'success': True, 
        'message': f'Updated {updated_count} resources with default category',
        'updated_count': updated_count
    }


@app.route('/cleanup-posts', methods=['POST'])
def cleanup_posts():
    """Admin route to clean up existing posts with unwanted characters"""
    if not session.get('logged_in') or not session.get('secret_admin'):
        return redirect(url_for('login'))
    
    posts = load_posts()
    cleaned_count = 0
    tag_fixes = 0
    comment_fixes = 0
    
    for post in posts:
        if 'content' in post:
            original_content = post['content']
            cleaned_content = clean_content(original_content)
            if original_content != cleaned_content:
                post['content'] = cleaned_content
                cleaned_count += 1
        
        if 'title' in post:
            post['title'] = post['title'].strip()
        
        # Ensure tags field exists and is a list
        if 'tags' not in post:
            post['tags'] = []
            tag_fixes += 1
        elif not isinstance(post['tags'], list):
            post['tags'] = []
            tag_fixes += 1
        
        # Ensure comments have IDs
        comments = post.get('comments', [])
        for comment in comments:
            if 'id' not in comment:
                comment['id'] = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
                comment_fixes += 1
    
    save_posts(posts)
    
    return {
        'success': True, 
        'message': f'Cleaned {cleaned_count} posts, fixed {tag_fixes} tag fields, added IDs to {comment_fixes} comments',
        'cleaned_count': cleaned_count,
        'tag_fixes': tag_fixes,
        'comment_fixes': comment_fixes
    }


@app.route('/edit/<int:index>', methods=['GET', 'POST'])
def edit_post(index):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    posts = load_posts()
    if index < 0 or index >= len(posts):
        return redirect(url_for('forum'))
    post = posts[index]
    if request.method == 'POST':
        if post.get('locked'):
            return redirect(url_for('forum'))
        
        # Debug: Log form data
        print(f"DEBUG: Editing post {index}")
        print(f"DEBUG: Form keys: {list(request.form.keys())}")
        print(f"DEBUG: Title: '{request.form.get('title', '')}'")
        print(f"DEBUG: Content length: {len(request.form.get('content', ''))}")
        print(f"DEBUG: Category: '{request.form.get('category', '')}'")
        print(f"DEBUG: Tag management mode: '{request.form.get('tag_management_mode', 'none')}'")
        
        # Clean the content to remove unwanted characters
        content = clean_content(request.form.get('content', ''))
        
        # Update post fields
        post['title'] = request.form.get('title', '').strip()
        post['content'] = content
        post['category'] = request.form.get('category', 'General')
        
        # Handle tags - check if this is coming from the new tag manager or old input
        if request.form.get('tag_management_mode') == 'api':
            # Tags are managed via API, don't override them here
            print("DEBUG: Using API tag management - skipping tag form processing")
        else:
            # Traditional tag input handling (backwards compatibility)
            tags_input = request.form.get('tags', '').strip()
            print(f"DEBUG: Traditional tags input: '{tags_input}'")
            if tags_input:
                # Split by comma and clean each tag
                new_tags = [t.strip() for t in tags_input.split(',') if t.strip()]
                post['tags'] = new_tags
                print(f"DEBUG: Set tags to: {new_tags}")
            else:
                # Explicitly clear tags when field is empty
                post['tags'] = []
                print("DEBUG: Cleared tags (empty input)")
        
        # Handle attachments and embedded images
        attachments = save_uploaded_files(request.files.getlist('attachments'))
        embedded = [f for f in request.form.get('embedded_images', '').split(',') if f]
        post.setdefault('attachments', []).extend(attachments)
        post.setdefault('embedded', []).extend(embedded)
        
        print(f"DEBUG: Saving post with title: '{post['title']}', content length: {len(post['content'])}")
        save_posts(posts)
        print("DEBUG: Posts saved successfully")
        return redirect(url_for('forum'))
    categories = load_categories()
    return render_template('newpost.html', post=post, index=index, categories=categories)


@app.route('/delete/<int:index>', methods=['POST'])
def delete_post(index):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    posts = load_posts()
    if index < 0 or index >= len(posts):
        return redirect(url_for('forum'))
    if posts[index].get('locked'):
        return redirect(url_for('forum'))
    posts.pop(index)
    save_posts(posts)
    return redirect(url_for('forum'))


@app.route('/lock/<int:index>', methods=['POST'])
def lock_post(index):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    posts = load_posts()
    if index < 0 or index >= len(posts):
        return redirect(url_for('forum'))
    posts[index]['locked'] = not posts[index].get('locked')
    save_posts(posts)
    return redirect(url_for('forum'))


@app.route('/post/<int:index>', methods=['GET', 'POST'])
def view_post(index):
    posts = load_posts()
    if index < 0 or index >= len(posts):
        return redirect(url_for('forum'))
    post = posts[index]
    if request.method == 'POST':
        name = request.form.get('name', 'Anonymous').strip() or 'Anonymous'
        text = request.form.get('comment', '').strip()
        if text:
            comment_id = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')  # Unique ID
            post.setdefault('comments', []).append({
                'id': comment_id,
                'name': name,
                'text': text,
                'created': datetime.utcnow().isoformat()
            })
            save_posts(posts)
            return redirect(url_for('view_post', index=index))
    comments = post.get('comments', [])
    return render_template('post.html', post=post, index=index, comments=comments)


@app.route('/delete-comment/<int:post_index>/<comment_id>', methods=['POST'])
def delete_comment(post_index, comment_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    posts = load_posts()
    if post_index < 0 or post_index >= len(posts):
        return redirect(url_for('forum'))
    
    post = posts[post_index]
    comments = post.get('comments', [])
    
    # Remove comment with matching ID
    post['comments'] = [c for c in comments if c.get('id') != comment_id]
    save_posts(posts)
    
    return redirect(url_for('view_post', index=post_index))


@app.route('/post-annotations/<int:index>', methods=['GET', 'POST', 'DELETE'])
def manage_post_annotations(index):
    """API endpoint for managing annotations on a specific post"""
    posts = load_posts()
    if index < 0 or index >= len(posts):
        return jsonify({'error': 'Post not found'}), 404
    
    post = posts[index]
    
    if request.method == 'GET':
        # Return current annotations
        return jsonify({
            'annotations': post.get('annotations', []),
            'post_title': post.get('title', 'Untitled')
        })
    
    elif request.method == 'POST':
        # Add a new annotation
        data = request.get_json() or {}
        
        if 'annotation' in data:
            annotation_id = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
            new_annotation = {
                'id': annotation_id,
                'type': data['annotation'].get('type', 'highlight'),  # highlight, drawing, note
                'data': data['annotation'].get('data', ''),
                'position': data['annotation'].get('position', {}),
                'color': data['annotation'].get('color', '#ffff00'),
                'author': session.get('username', 'Anonymous'),
                'created': datetime.utcnow().isoformat()
            }
            
            post.setdefault('annotations', []).append(new_annotation)
            save_posts(posts)
            return jsonify({'success': True, 'annotation': new_annotation})
        
        else:
            return jsonify({'error': 'No annotation data provided'}), 400
    
    elif request.method == 'DELETE':
        # Remove a specific annotation
        if not session.get('logged_in'):
            return jsonify({'error': 'Not authenticated'}), 401
            
        data = request.get_json() or {}
        annotation_id = data.get('annotation_id', '')
        
        if annotation_id:
            annotations = post.get('annotations', [])
            post['annotations'] = [a for a in annotations if a.get('id') != annotation_id]
            save_posts(posts)
            return jsonify({'success': True, 'annotations': post['annotations']})
        else:
            return jsonify({'error': 'Annotation ID not found'}), 404
    
    # This should never be reached, but return error just in case
    return jsonify({'error': 'Invalid request method'}), 405


@app.route('/resources/<path:filename>')
def resources(filename):
    return send_from_directory(app.root_path, filename)


@app.route('/check-external-features')
def check_external_features():
    """Check if current user has external features enabled."""
    if not session.get('logged_in'):
        return jsonify({'has_external_features': False})
    
    # Secret admins (using master password) always have external features access
    if session.get('secret_admin'):
        return jsonify({'has_external_features': True})
    
    username = session.get('username')
    try:
        from db_utils import get_user_by_username
        user = get_user_by_username(username)
        has_external = user and user.get('external_features', 0) == 1
        return jsonify({'has_external_features': has_external})
    except Exception as e:
        print(f"Error checking external features for {username}: {e}")
        return jsonify({'has_external_features': False})



@app.route('/api/external-tools')
def get_external_tools():
    """Get available external tools for the current user."""
    if not session.get('logged_in'):
        return jsonify({'hasAccess': False, 'error': 'Not authenticated'}), 401
    
    username = session.get('username')
    has_external = False
    
    # Secret admins (using master password) always have external features access
    if session.get('secret_admin'):
        has_external = True
    else:
        try:
            from db_utils import get_user_by_username
            user = get_user_by_username(username)
            has_external = user and user.get('external_features', 0) == 1
        except Exception as e:
            print(f"Error getting external tools for {username}: {e}")
            return jsonify({'hasAccess': False, 'error': str(e)}), 500
    
    if not has_external:
        return jsonify({'hasAccess': False, 'tools': []})
    
    # Load tools from configuration file and user tools
    config = load_external_tools_config()
    
    # Get server tools (excluding hidden ones for UI display)
    server_tools = [
        tool for tool in config.get('server_tools', []) 
        if tool.get('enabled', False) and not tool.get('hidden', False)
    ]
    
    # Get user tools if enabled
    user_tools = []
    if config.get('settings', {}).get('allow_user_tools', True):
        try:
            from db_utils import get_user_external_tools
            user_tools = [
                tool for tool in get_user_external_tools(username)
                if tool.get('is_enabled', 1) == 1
            ]
        except Exception as e:
            print(f"Error loading user tools for {username}: {e}")
    
    # Combine all tools
    all_tools = server_tools + user_tools
    
    return jsonify({
        'hasAccess': True,
        'tools': all_tools,
        'username': username,
        'server_tools_count': len(server_tools),
        'user_tools_count': len(user_tools)
    })


@app.route('/api/external-tools/run', methods=['POST'])
def run_external_tool():
    """Execute an external tool."""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    username = session.get('username')
    has_external = False
    
    # Secret admins (using master password) always have external features access
    if session.get('secret_admin'):
        has_external = True
    else:
        try:
            from db_utils import get_user_by_username
            user = get_user_by_username(username)
            has_external = user and user.get('external_features', 0) == 1
        except Exception as e:
            print(f"Error checking external features for {username}: {e}")
            return jsonify({'success': False, 'error': 'Database error'}), 500
    
    if not has_external:
        return jsonify({'success': False, 'error': 'External tools not enabled'}), 403
    
    try:
        data = request.get_json()
        tool_id = data.get('toolId')
        
        if not tool_id:
            return jsonify({'success': False, 'error': 'Tool ID required'}), 400
        
        # Load tool configuration from server tools first
        config = load_external_tools_config()
        tool_config = None
        tool_source = None
        
        # Check server tools (including hidden ones)
        for tool in config.get('server_tools', []):
            if tool.get('id') == tool_id and tool.get('enabled', False):
                tool_config = tool
                tool_source = 'server'
                break
        
        # If not found in server tools, check user tools
        if not tool_config:
            try:
                from db_utils import get_user_external_tools
                user_tools = get_user_external_tools(username)
                for tool in user_tools:
                    if tool.get('tool_id') == tool_id and tool.get('is_enabled', 1) == 1:
                        tool_config = tool
                        tool_source = 'user'
                        break
            except Exception as e:
                print(f"Error loading user tools for execution: {e}")
        
        if not tool_config:
            return jsonify({'success': False, 'error': 'Tool not found or disabled'}), 400
        
        # Handle different tool types
        tool_type = tool_config.get('type', 'system')
        
        # Log tool usage if enabled
        if config.get('settings', {}).get('log_tool_usage', True):
            print(f"User {username} executed {tool_source} tool: {tool_id} (type: {tool_type})")
        
        # Get executable/URL based on tool source and type
        if tool_source == 'server':
            executable_path = tool_config.get('executable')
            website_url = tool_config.get('website_url')
        else:  # user tool
            executable_path = tool_config.get('executable_path')
            website_url = tool_config.get('website_url')
        
        # Handle different tool types
        if tool_type == 'website':
            if not website_url:
                return jsonify({'success': False, 'error': 'Website URL not configured'}), 400
                
            return jsonify({
                'success': True,
                'action': 'open_url',
                'url': website_url,
                'message': f'Opening {tool_config.get("name", tool_id)} in browser'
            })
        
        elif tool_type == 'protocol':
            protocol_url = tool_config.get('protocol_url', '')
            if not protocol_url:
                return jsonify({'success': False, 'error': 'Protocol URL not configured'}), 400
                
            return jsonify({
                'success': True,
                'action': 'protocol',
                'url': protocol_url,
                'message': f'Launching {tool_config.get("name", tool_id)} via protocol'
            })
        
        elif tool_type == 'client_service':
            # Queue command for client service execution
            global CLIENT_SERVICE_QUEUE
            
            if username not in CLIENT_SERVICE_QUEUE:
                CLIENT_SERVICE_QUEUE[username] = []
            
            
            # Create command for client service
            command = {
                'id': datetime.utcnow().strftime('%Y%m%d%H%M%S%f'),
                'type': 'command',
                'created': datetime.utcnow().isoformat(),
                'status': 'pending'
            }
            # Create generic tool command
            tool_executable = executable_path or tool_id
            command["command"] = f"cmd|tool|{tool_id}|{tool_executable}|launch"
            
            CLIENT_SERVICE_QUEUE[username].append(command)
            
            return jsonify({
                'success': True,
                'action': 'client_service',
                'tool_id': tool_id,
                'command_id': command['id'],
                'message': f'Tool {tool_config.get("name", tool_id)} queued for client service execution'
            })
        elif tool_type == 'executable' or tool_type == 'script':
            # Handle executable tools
            if not executable_path:
                return jsonify({'success': False, 'error': 'Executable path not configured'}), 400
                
            return jsonify({
                'success': True,
                'action': 'execute',
                'executable': executable_path,
                'message': f'Tool {tool_config.get("name", tool_id)} execution requested'
            })
        else:
            return jsonify({'success': False, 'error': f'Unknown tool type: {tool_type}'}), 400
        
    except Exception as e:
        print(f"Error running external tool for {username}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/client-service/queue', methods=['GET', 'POST'])
def client_service_queue():
    """Handle client service tool execution queue."""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    username = session.get('username')
    has_external = False
    
    # Secret admins (using master password) always have external features access
    if session.get('secret_admin'):
        has_external = True
    else:
        try:
            from db_utils import get_user_by_username
            user = get_user_by_username(username)
            has_external = user and user.get('external_features', 0) == 1
        except Exception as e:
            print(f"Error checking external features for {username}: {e}")
            return jsonify({'success': False, 'error': 'Database error'}), 500
    
    if not has_external:
        return jsonify({'success': False, 'error': 'External tools not enabled'}), 403
    
    try:
        # Simple in-memory queue (in production, use Redis or database)
        global CLIENT_SERVICE_QUEUE
        
        if request.method == 'GET':
            # Return pending tasks for this user
            user_queue = CLIENT_SERVICE_QUEUE.get(username, [])
            return jsonify({
                'success': True,
                'queue': user_queue,
                'count': len(user_queue)
            })
            
        elif request.method == 'POST':
            # Add task to queue or mark task as completed
            data = request.get_json()
            action = data.get('action', 'add')
            
            if action == 'add':
                tool_id = data.get('tool_id')
                if not tool_id:
                    return jsonify({'success': False, 'error': 'Tool ID required'}), 400
                
                # Add task to user's queue
                if username not in CLIENT_SERVICE_QUEUE:
                    CLIENT_SERVICE_QUEUE[username] = []
                
                task = {
                    'id': datetime.utcnow().strftime('%Y%m%d%H%M%S%f'),
                    'tool_id': tool_id,
                    'created': datetime.utcnow().isoformat(),
                    'status': 'pending'
                }
                
                CLIENT_SERVICE_QUEUE[username].append(task)
                
                print(f"Added task to queue for {username}: {tool_id}")
                
                return jsonify({
                    'success': True,
                    'task_id': task['id'],
                    'message': 'Task added to queue'
                })
                
            elif action == 'complete':
                task_id = data.get('task_id')
                if not task_id:
                    return jsonify({'success': False, 'error': 'Task ID required'}), 400
                
                # Remove completed task from queue
                user_queue = CLIENT_SERVICE_QUEUE.get(username, [])
                CLIENT_SERVICE_QUEUE[username] = [
                    task for task in user_queue if task.get('id') != task_id
                ]
                
                return jsonify({
                    'success': True,
                    'message': 'Task marked as completed'
                })
            
            else:
                return jsonify({'success': False, 'error': 'Invalid action'}), 400
        
    except Exception as e:
        print(f"Error in client service queue for {username}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
    # Default return for unsupported HTTP methods
    return jsonify({'success': False, 'error': 'Method not allowed'}), 405


@app.route('/admin/external-tools', methods=['GET', 'POST'])
def manage_external_tools():
    """Admin interface for managing server-wide external tools configuration."""
    if not session.get('logged_in') or not session.get('secret_admin'):
        return redirect(url_for('login'))
    
    config = load_external_tools_config()
    error = None
    success = None
    
    if request.method == 'POST':
        action = request.form.get('action', '')
        
        try:
            if action == 'update_tool':
                tool_id = request.form.get('tool_id', '')
                enabled = bool(request.form.get('enabled'))
                hidden = bool(request.form.get('hidden'))
                
                # Find and update server tool
                for tool in config.get('server_tools', []):
                    if tool.get('id') == tool_id:
                        tool['enabled'] = enabled
                        tool['hidden'] = hidden
                        break
                
                if save_external_tools_config(config):
                    success = f"Tool {tool_id} updated successfully"
                else:
                    error = "Failed to save configuration"
                    
            elif action == 'add_tool':
                new_tool = {
                    'id': request.form.get('new_tool_id', '').strip(),
                    'name': request.form.get('new_tool_name', '').strip(),
                    'description': request.form.get('new_tool_description', '').strip(),
                    'icon': request.form.get('new_tool_icon', 'bi bi-gear').strip(),
                    'type': request.form.get('new_tool_type', 'executable'),
                    'executable': request.form.get('new_tool_executable', '').strip(),
                    'website_url': request.form.get('new_tool_website_url', '').strip(),
                    'enabled': bool(request.form.get('new_tool_enabled')),
                    'hidden': bool(request.form.get('new_tool_hidden'))
                }
                
                # Validate required fields based on type
                if not all([new_tool['id'], new_tool['name']]):
                    error = "Tool ID and name are required"
                elif new_tool['type'] == 'website' and not new_tool['website_url']:
                    error = "Website URL is required for website tools"
                elif new_tool['type'] in ['executable', 'script'] and not new_tool['executable']:
                    error = "Executable path is required for executable/script tools"
                else:
                    # Check for duplicate ID
                    existing_ids = [tool.get('id') for tool in config.get('server_tools', [])]
                    if new_tool['id'] in existing_ids:
                        error = "Tool ID already exists"
                    else:
                        config.setdefault('server_tools', []).append(new_tool)
                        if save_external_tools_config(config):
                            success = f"Tool {new_tool['name']} added successfully"
                        else:
                            error = "Failed to save configuration"
                            
            elif action == 'delete_tool':
                tool_id = request.form.get('tool_id', '')
                config['server_tools'] = [tool for tool in config.get('server_tools', []) if tool.get('id') != tool_id]
                
                if save_external_tools_config(config):
                    success = f"Tool {tool_id} deleted successfully"
                else:
                    error = "Failed to save configuration"
                    
            elif action == 'update_settings':
                settings = config.setdefault('settings', {})
                settings['allow_user_tools'] = bool(request.form.get('allow_user_tools'))
                settings['max_user_tools'] = int(request.form.get('max_user_tools', 10))
                settings['log_tool_usage'] = bool(request.form.get('log_tool_usage'))
                
                if save_external_tools_config(config):
                    success = "Settings updated successfully"
                else:
                    error = "Failed to save settings"
                    
        except Exception as e:
            error = f"Error: {str(e)}"
    
    return render_template('admin_external_tools.html', 
                         config=config, 
                         error=error, 
                         success=success)




@app.route('/client_tools/<path:filename>')
def client_tools(filename):
    """Serve client tools files for download"""
    if not session.get('logged_in'):
        return jsonify({'error': 'Not authenticated'}), 401
    
    username = session.get('username')
    has_external = False
    
    # Check external features access
    if session.get('secret_admin'):
        has_external = True
    else:
        try:
            from db_utils import get_user_by_username
            user = get_user_by_username(username)
            has_external = user and user.get('external_features', 0) == 1
        except Exception as e:
            print(f"Error checking external features for {username}: {e}")
            return jsonify({'error': 'Database error'}), 500
    
    if not has_external:
        return jsonify({'error': 'External features not enabled'}), 403
    
    client_tools_dir = os.path.join(app.root_path, 'client_tools')
    return send_from_directory(client_tools_dir, filename)




@app.route('/uploads/<path:filename>')
def uploads(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route('/upload-image', methods=['POST'])
def upload_image():
    if not session.get('logged_in'):
        return {'error': 'Not authenticated'}, 401
    
    file = request.files.get('image')
    if not file:
        return {'error': 'No file provided'}, 400
    
    # Handle cases where filename might be empty or None
    original_filename = file.filename or 'pasted_image'
    
    # For pasted images, we might not have a proper extension
    if '.' not in original_filename:
        # Try to detect content type and add appropriate extension
        content_type = file.content_type or 'image/png'
        if 'image/jpeg' in content_type or 'image/jpg' in content_type:
            original_filename += '.jpg'
        elif 'image/gif' in content_type:
            original_filename += '.gif'
        elif 'image/webp' in content_type:
            original_filename += '.webp'
        else:
            original_filename += '.png'  # default to png
    
    # Check if file type is allowed (expand for image types)
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'tiff', 'svg'}
    if '.' in original_filename:
        ext = original_filename.rsplit('.', 1)[1].lower()
        if ext not in allowed_extensions:
            return {'error': f'File type {ext} not allowed'}, 400
    
    # Generate unique filename
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    name = f"{timestamp}_{secure_filename(original_filename)}"
    path = os.path.join(UPLOAD_FOLDER, name)
    
    try:
        file.save(path)
        return {
            'url': url_for('uploads', filename=name), 
            'filename': name,
            'success': True
        }
    except Exception as e:
        return {'error': f'Failed to save file: {str(e)}'}, 500


def get_local_ip():
    """Automatically detect the local IP address"""
    try:
        # Connect to a remote address to determine which interface to use
        # This doesn't actually send data, just determines routing
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            # Use Google's DNS server as a reference point
            s.connect(('8.8.8.8', 80))
            local_ip = s.getsockname()[0]
            return local_ip
    except Exception:
        # Fallback methods if the above fails
        try:
            # Try getting hostname IP
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            # Avoid localhost IPs
            if local_ip.startswith('127.'):
                # Try getting all IP addresses for the hostname
                all_ips = socket.gethostbyname_ex(hostname)[2]
                for ip in all_ips:
                    if not ip.startswith('127.'):
                        return ip
            return local_ip
        except Exception:
            # Last resort - return localhost
            return '127.0.0.1'


# Custom Data Tables Management Routes

@app.route('/admin/data-tables', methods=['GET', 'POST'])
def manage_data_tables():
    """Admin interface for managing custom data tables."""
    if not session.get('logged_in') or not session.get('secret_admin'):
        return redirect(url_for('login'))
    
    error = None
    success = None
    
    if request.method == 'POST':
        action = request.form.get('action', '')
        
        if action == 'create':
            table_name = request.form.get('table_name', '').strip()
            description = request.form.get('description', '').strip()
            
            # Parse columns from form
            columns = []
            column_count = int(request.form.get('column_count', 0))
            
            for i in range(column_count):
                col_name = request.form.get(f'column_{i}_name', '').strip()
                col_type = request.form.get(f'column_{i}_type', 'string')
                col_required = bool(request.form.get(f'column_{i}_required'))
                col_unique = bool(request.form.get(f'column_{i}_unique'))
                
                if col_name:
                    columns.append({
                        'name': col_name,
                        'type': col_type,
                        'required': col_required,
                        'unique': col_unique
                    })
            
            if table_name and columns:
                try:
                    from db_utils import create_custom_table
                    success_flag, message = create_custom_table(table_name, columns, description)
                    if success_flag:
                        success = message
                    else:
                        error = message
                except Exception as e:
                    error = f"Error creating table: {str(e)}"
            else:
                error = "Table name and at least one column are required"
                
        elif action == 'delete':
            table_name = request.form.get('table_name', '').strip()
            if table_name:
                try:
                    from db_utils import delete_custom_table
                    success_flag, message = delete_custom_table(table_name)
                    if success_flag:
                        success = message
                    else:
                        error = message
                except Exception as e:
                    error = f"Error deleting table: {str(e)}"
    
    # Load existing tables
    try:
        from db_utils import get_custom_tables
        tables = get_custom_tables()
    except Exception as e:
        print(f"Error loading custom tables: {e}")
        tables = []
        error = "Error loading tables from database"
    
    return render_template('admin_data_tables.html', 
                         tables=tables,
                         error=error, 
                         success=success)


@app.route('/admin/data-tables/<table_name>', methods=['GET', 'POST'])
def manage_table_data(table_name):
    """Interface for managing data in a specific custom table."""
    if not session.get('logged_in') or not session.get('secret_admin'):
        return redirect(url_for('login'))
    
    error = None
    success = None
    
    # Get table metadata
    try:
        from db_utils import get_custom_tables
        tables = get_custom_tables()
        table_info = next((t for t in tables if t['table_name'] == table_name), None)
        if not table_info:
            return redirect(url_for('manage_data_tables'))
    except Exception as e:
        return redirect(url_for('manage_data_tables'))
    
    if request.method == 'POST':
        action = request.form.get('action', '')
        
        if action == 'add_row':
            # Parse row data from form
            row_data = {}
            for column in table_info['columns']:
                col_name = column['name']
                value = request.form.get(col_name, '').strip()
                
                # Type conversion
                if column['type'] == 'integer' and value:
                    try:
                        value = int(value)
                    except ValueError:
                        error = f"Invalid integer value for {col_name}"
                        break
                elif column['type'] == 'decimal' and value:
                    try:
                        value = float(value)
                    except ValueError:
                        error = f"Invalid decimal value for {col_name}"
                        break
                elif column['type'] == 'boolean':
                    value = bool(request.form.get(col_name))
                
                # Check required fields
                if column.get('required') and not value:
                    error = f"Field {col_name} is required"
                    break
                
                row_data[col_name] = value
            
            if not error:
                try:
                    from db_utils import insert_custom_table_row
                    success_flag, message = insert_custom_table_row(
                        table_name, 
                        row_data, 
                        session.get('username', 'admin')
                    )
                    if success_flag:
                        success = message
                    else:
                        error = message
                except Exception as e:
                    error = f"Error adding row: {str(e)}"
    
    # Get table data
    try:
        from db_utils import get_custom_table_data
        page = int(request.args.get('page', 1))
        per_page = 20
        offset = (page - 1) * per_page
        
        result, err = get_custom_table_data(table_name, limit=per_page, offset=offset)
        if err:
            error = err
            table_data = {'data': [], 'total': 0}
        else:
            table_data = result
    except Exception as e:
        error = f"Error loading table data: {str(e)}"
        table_data = {'data': [], 'total': 0}
    
    # Calculate pagination
    if table_data and 'total' in table_data:
        total_pages = (table_data['total'] + per_page - 1) // per_page
        pagination = {
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'total_rows': table_data['total'],
            'has_prev': page > 1,
            'has_next': page < total_pages,
            'prev_num': page - 1 if page > 1 else None,
            'next_num': page + 1 if page < total_pages else None
        }
    else:
        pagination = {
            'page': 1,
            'per_page': per_page,
            'total_pages': 1,
            'total_rows': 0,
            'has_prev': False,
            'has_next': False,
            'prev_num': None,
            'next_num': None
        }
    
    return render_template('admin_table_data.html',
                         table_info=table_info,
                         table_data=table_data,
                         pagination=pagination,
                         error=error,
                         success=success)




@app.route('/api/data-tables')
def api_get_data_tables():
    """API endpoint to get list of custom data tables for other integrations."""
    if not session.get('logged_in'):
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from db_utils import get_custom_tables
        tables = get_custom_tables()
        
        # Format for API consumption
        api_tables = []
        for table in tables:
            api_tables.append({
                'table_name': table['table_name'],
                'display_name': table['display_name'],
                'description': table['description'],
                'row_count': table['row_count'],
                'columns': table['columns']
            })
        
        return jsonify({
            'success': True,
            'tables': api_tables,
            'count': len(api_tables)
        })
        
    except Exception as e:
        print(f"Error in API get data tables: {e}")
        return jsonify({'error': 'Failed to load tables'}), 500


@app.route('/api/data-tables/<table_name>/data')
def api_get_table_data(table_name):
    """API endpoint to get data from a specific custom table."""
    if not session.get('logged_in'):
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from db_utils import get_custom_table_for_reference
        data, error = get_custom_table_for_reference(table_name)
        
        if error:
            return jsonify({'error': error}), 404
        
        return jsonify({
            'success': True,
            'table_data': data
        })
        
    except Exception as e:
        print(f"Error in API get table data for {table_name}: {e}")
        return jsonify({'error': 'Failed to load table data'}), 500


@app.route('/api/data-tables/<table_name>/related')
def api_get_related_data(table_name):
    """Return a single row from a table matching a column value."""
    if not session.get('logged_in'):
        return jsonify({'error': 'Not authenticated'}), 401

    column = request.args.get('column', '')
    value = request.args.get('value', '')
    return_cols = request.args.getlist('return')

    try:
        from db_utils import get_custom_table_related_data
        row = get_custom_table_related_data(f"custom_{table_name}", column, value, return_cols)
        if row is None:
            return jsonify({'success': True, 'row': None})
        return jsonify({'success': True, 'row': row})
    except Exception as e:
        print(f"Error getting related data for {table_name}: {e}")
        return jsonify({'error': 'Failed to get related data'}), 500


if __name__ == '__main__':
    # Automatically detect local IP address
    auto_ip = get_local_ip()
    host = os.environ.get('TRUCKSOFT_HOST', auto_ip)
    port = int(os.environ.get('TRUCKSOFT_PORT', '5151'))
    
    print(f"Starting server on {host}:{port}")
    print(f"Auto-detected IP: {auto_ip}")
    if host != auto_ip:
        print(f"Using environment override: {host}")
    
    app.run(host=host, port=port, debug=True)