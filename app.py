import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from models import db, User, FoodItem, Table, Reservation, Order, OrderItem
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dineease_super_secret_key_12345'

# Use external Database if provided (e.g. Supabase, Vercel Postgres)
if os.environ.get('DATABASE_URL'):
    db_url = os.environ.get('DATABASE_URL')
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
# Vercel provides a read-only filesystem, except for /tmp
elif os.environ.get('VERCEL') == '1':
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/dineease.db'
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dineease.db'
    
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Context processor to inject cart count into all templates
@app.context_processor
def inject_cart_count():
    cart = session.get('cart', {})
    cart_count = sum(cart.values())
    return dict(cart_count=cart_count)

@app.before_request
def initialize_vercel_db():
    # Auto-initialize database on Vercel cold starts
    if os.environ.get('VERCEL') == '1' and not getattr(app, '_vercel_db_initialized', False):
        try:
            db.create_all()
            if not User.query.filter_by(email='admin@dineease.com').first():
                hashed_pw = bcrypt.generate_password_hash('admin123').decode('utf-8')
                admin = User(username='admin', email='admin@dineease.com', password=hashed_pw, role='admin')
                db.session.add(admin)
                
            if not Table.query.first():
                for i in range(1, 11):
                    capacity = 2 if i <= 4 else (4 if i <= 8 else 6)
                    db.session.add(Table(table_number=i, capacity=capacity))
                    
            if not FoodItem.query.first():
                mock_foods = [
                    FoodItem(name='Classic Pancakes', description='Fluffy pancakes served with maple syrup and butter.', price=12.00, category='Breakfast', image_url='https://images.unsplash.com/photo-1528207776546-365bb710ee93?w=500', rating=4.8, diet_type='Veg'),
                    FoodItem(name='Bacon & Eggs', description='Crispy bacon with sunny-side-up eggs.', price=14.00, category='Breakfast', image_url='https://images.unsplash.com/photo-1525351484163-7529414344d8?w=500', rating=4.7, diet_type='Non-Veg'),
                    FoodItem(name='Masala Dosa', description='Crispy rice crepe filled with spiced potato masala.', price=10.00, category='Breakfast', image_url='https://images.unsplash.com/photo-1589301760014-d929f39ce9b1?w=500', rating=4.9, diet_type='Veg'),
                    FoodItem(name='Hyderabadi Chicken Biryani', description='Aromatic basmati rice cooked with tender chicken and authentic spices.', price=18.00, category='Lunch', image_url='https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=500', rating=4.9, diet_type='Non-Veg'),
                    FoodItem(name='Paneer Tikka Masala', description='Grilled cottage cheese in a spicy, flavorful sauce.', price=16.00, category='Lunch', image_url='https://images.unsplash.com/photo-1565557623262-b51c2513a641?w=500', rating=4.7, diet_type='Veg'),
                    FoodItem(name='Grilled Salmon Salad', description='Fresh greens topped with perfectly grilled salmon.', price=20.00, category='Lunch', image_url='https://images.unsplash.com/photo-1467003909585-2f8a72700288?w=500', rating=4.6, diet_type='Non-Veg'),
                    FoodItem(name='Truffle Risotto', description='Creamy arborio rice with black truffle shavings.', price=28.50, category='Dinner', image_url='https://images.unsplash.com/photo-1626082927389-6cd097cdc6ec?w=500', rating=4.8, diet_type='Veg'),
                    FoodItem(name='Wagyu Beef Steak', description='Premium grade wagyu, grilled to perfection.', price=55.00, category='Dinner', image_url='https://images.unsplash.com/photo-1544025162-d76694265947?w=500', rating=4.9, diet_type='Non-Veg'),
                    FoodItem(name='Margherita Pizza', description='Classic wood-fired pizza with fresh mozzarella and basil.', price=18.00, category='Dinner', image_url='https://images.unsplash.com/photo-1574071318508-1cdbab80d002?w=500', rating=4.7, diet_type='Veg'),
                    FoodItem(name='Molten Lava Cake', description='Rich chocolate cake with a gooey center, served with vanilla ice cream.', price=15.00, category='Desserts', image_url='https://images.unsplash.com/photo-1624353365286-3f8d62daad51?w=500', rating=4.9, diet_type='Veg'),
                    FoodItem(name='Signature Gold Cocktail', description='A mix of premium spirits with edible gold flakes.', price=30.00, category='Beverages', image_url='https://images.unsplash.com/photo-1514362545857-3bc16c4c7d1b?w=500', rating=4.8, diet_type='Veg')
                ]
                db.session.add_all(mock_foods)
            db.session.commit()
            app._vercel_db_initialized = True
        except Exception as e:
            print("Error initializing DB on Vercel:", e)

# --- Routes ---
@app.route('/')
def home():
    featured_foods = FoodItem.query.limit(4).all()
    return render_template('home.html', featured_foods=featured_foods)

@app.route('/menu')
def menu():
    categories = ['Breakfast', 'Lunch', 'Dinner', 'Dessert', 'Beverage']
    foods = FoodItem.query.filter_by(is_deleted=False).all()
    return render_template('menu.html', foods=foods, categories=categories)

@app.route('/booking', methods=['GET', 'POST'])
def booking():
    if request.method == 'POST':
        date = request.form.get('date')
        time = request.form.get('time')
        guests = request.form.get('guests')
        table_id = request.form.get('table_id')

        if date and time and guests and table_id:
            user_id = current_user.id if current_user.is_authenticated else None
            reservation = Reservation(user_id=user_id, table_id=table_id, date=date, time=time, guests=guests)
            db.session.add(reservation)
            db.session.commit()
            flash('Table booked successfully!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Please fill all fields', 'danger')

    tables = Table.query.all()
    reservations = Reservation.query.filter_by(status='confirmed').all()
    reservations_data = [{'table_id': r.table_id, 'date': r.date, 'time': r.time} for r in reservations]
    return render_template('booking.html', tables=tables, reservations_data=reservations_data)

@app.route('/cart')
def cart():
    cart_data = session.get('cart', {})
    items = []
    total = 0
    for food_id, quantity in cart_data.items():
        food = FoodItem.query.get(int(food_id))
        if food:
            subtotal = food.price * quantity
            total += subtotal
            items.append({'food': food, 'quantity': quantity, 'subtotal': subtotal})
    return render_template('cart.html', items=items, total=total)

@app.route('/add_to_cart/<int:food_id>', methods=['POST'])
def add_to_cart(food_id):
    cart = session.get('cart', {})
    food_id_str = str(food_id)
    if food_id_str in cart:
        cart[food_id_str] += 1
    else:
        cart[food_id_str] = 1
    session['cart'] = cart
    return jsonify({'success': True, 'cart_count': sum(cart.values())})

@app.route('/update_cart/<int:food_id>', methods=['POST'])
def update_cart(food_id):
    data = request.get_json()
    action = data.get('action')
    cart = session.get('cart', {})
    food_id_str = str(food_id)
    
    if food_id_str in cart:
        if action == 'increase':
            cart[food_id_str] += 1
        elif action == 'decrease':
            cart[food_id_str] -= 1
            if cart[food_id_str] <= 0:
                del cart[food_id_str]
        elif action == 'remove':
            del cart[food_id_str]
    
    session['cart'] = cart
    # Calculate new total
    total = 0
    for fid, quantity in cart.items():
        food = FoodItem.query.get(int(fid))
        if food:
            total += food.price * quantity
            
    return jsonify({'success': True, 'cart_count': sum(cart.values()), 'new_total': total})

@app.route('/checkout', methods=['POST'])
def checkout():
    cart = session.get('cart', {})
    if not cart:
        flash('Your cart is empty', 'warning')
        return redirect(url_for('cart'))
        
    total = 0
    order_items = []
    for fid, quantity in cart.items():
        food = FoodItem.query.get(int(fid))
        if food:
            total += food.price * quantity
            order_items.append((food, quantity))
    user_id = current_user.id if current_user.is_authenticated else None
    order = Order(user_id=user_id, total_amount=total)
    db.session.add(order)
    db.session.commit()
    
    for food, quantity in order_items:
        order_item = OrderItem(order_id=order.id, food_item_id=food.id, quantity=quantity, price=food.price)
        db.session.add(order_item)
        
    db.session.commit()
    session['cart'] = {} # clear cart
    flash('Order placed successfully! Paid via Demo Payment.', 'success')
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    reservations = Reservation.query.filter_by(user_id=current_user.id).all()
    orders = Order.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', reservations=reservations, orders=orders)

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('home'))
    foods = FoodItem.query.filter_by(is_deleted=False).all()
    removed_foods = FoodItem.query.filter_by(is_deleted=True).all()
    reservations = Reservation.query.all()
    orders = Order.query.all()
    users = User.query.all()
    return render_template('admin_dashboard.html', foods=foods, removed_foods=removed_foods, reservations=reservations, orders=orders, users=users)

# --- Auth Routes ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('auth.html', is_login=True)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        # Check if user exists
        if User.query.filter_by(email=email).first() or User.query.filter_by(username=username).first():
            flash('Email or username already exists.', 'danger')
            return redirect(url_for('register'))
            
        user = User(username=username, email=email, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('auth.html', is_login=False)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))

# --- Admin actions ---
@app.route('/admin/add_food', methods=['POST'])
@login_required
def add_food():
    if current_user.role != 'admin':
        return redirect(url_for('home'))
    
    name = request.form.get('name')
    description = request.form.get('description', '')
    price = request.form.get('price')
    category = request.form.get('category')
    image_url = request.form.get('image_url')
    diet_type = request.form.get('diet_type')
    
    food = FoodItem(name=name, description=description, price=float(price), category=category, image_url=image_url, diet_type=diet_type)
    db.session.add(food)
    db.session.commit()
    flash('Food item added!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_food/<int:id>', methods=['POST'])
@login_required
def delete_food(id):
    if current_user.role != 'admin':
        return redirect(url_for('home'))
    food = FoodItem.query.get_or_404(id)
    food.is_deleted = True
    db.session.commit()
    flash('Food item removed!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/restore_food/<int:id>', methods=['POST'])
@login_required
def restore_food(id):
    if current_user.role != 'admin':
        return redirect(url_for('home'))
    food = FoodItem.query.get_or_404(id)
    food.is_deleted = False
    db.session.commit()
    flash('Food item restored!', 'success')
    return redirect(url_for('admin_dashboard'))

# Database initialization route (run once)
@app.route('/initdb')
def initdb():
    db.create_all()
    
    # Create admin user
    if not User.query.filter_by(email='admin@dineease.com').first():
        hashed_pw = bcrypt.generate_password_hash('admin123').decode('utf-8')
        admin = User(username='admin', email='admin@dineease.com', password=hashed_pw, role='admin')
        db.session.add(admin)
        
    # Create mock tables if none exist
    if not Table.query.first():
        for i in range(1, 11):
            capacity = 2 if i <= 4 else (4 if i <= 8 else 6)
            db.session.add(Table(table_number=i, capacity=capacity))
            
    # Create mock food if none exist
    if not FoodItem.query.first():
        mock_foods = [
            # Breakfast
            FoodItem(name='Classic Pancakes', description='Fluffy pancakes served with maple syrup and butter.', price=12.00, category='Breakfast', image_url='https://images.unsplash.com/photo-1528207776546-365bb710ee93?w=500', rating=4.8, diet_type='Veg'),
            FoodItem(name='Bacon & Eggs', description='Crispy bacon with sunny-side-up eggs.', price=14.00, category='Breakfast', image_url='https://images.unsplash.com/photo-1525351484163-7529414344d8?w=500', rating=4.7, diet_type='Non-Veg'),
            FoodItem(name='Masala Dosa', description='Crispy rice crepe filled with spiced potato masala.', price=10.00, category='Breakfast', image_url='https://images.unsplash.com/photo-1589301760014-d929f39ce9b1?w=500', rating=4.9, diet_type='Veg'),
            
            # Lunch
            FoodItem(name='Hyderabadi Chicken Biryani', description='Aromatic basmati rice cooked with tender chicken and authentic spices.', price=18.00, category='Lunch', image_url='https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=500', rating=4.9, diet_type='Non-Veg'),
            FoodItem(name='Paneer Tikka Masala', description='Grilled cottage cheese in a spicy, flavorful sauce.', price=16.00, category='Lunch', image_url='https://images.unsplash.com/photo-1565557623262-b51c2513a641?w=500', rating=4.7, diet_type='Veg'),
            FoodItem(name='Grilled Salmon Salad', description='Fresh greens topped with perfectly grilled salmon.', price=20.00, category='Lunch', image_url='https://images.unsplash.com/photo-1467003909585-2f8a72700288?w=500', rating=4.6, diet_type='Non-Veg'),

            # Dinner
            FoodItem(name='Truffle Risotto', description='Creamy arborio rice with black truffle shavings.', price=28.50, category='Dinner', image_url='https://images.unsplash.com/photo-1626082927389-6cd097cdc6ec?w=500', rating=4.8, diet_type='Veg'),
            FoodItem(name='Wagyu Beef Steak', description='Premium grade wagyu, grilled to perfection.', price=55.00, category='Dinner', image_url='https://images.unsplash.com/photo-1544025162-d76694265947?w=500', rating=4.9, diet_type='Non-Veg'),
            FoodItem(name='Margherita Pizza', description='Classic wood-fired pizza with fresh mozzarella and basil.', price=18.00, category='Dinner', image_url='https://images.unsplash.com/photo-1574071318508-1cdbab80d002?w=500', rating=4.7, diet_type='Veg'),
            
            # Desserts
            FoodItem(name='Molten Lava Cake', description='Rich chocolate cake with a gooey center, served with vanilla ice cream.', price=15.00, category='Desserts', image_url='https://images.unsplash.com/photo-1624353365286-3f8d62daad51?w=500', rating=4.9, diet_type='Veg'),
            FoodItem(name='Classic Tiramisu', description='Layers of espresso-soaked ladyfingers and mascarpone cream.', price=12.00, category='Desserts', image_url='https://images.unsplash.com/photo-1571115177098-24ec42ed204d?w=500', rating=4.7, diet_type='Veg'),
            FoodItem(name='Creme Brulee', description='Rich vanilla custard topped with a layer of hard caramel.', price=14.00, category='Desserts', image_url='https://images.unsplash.com/photo-1551024601-bec78aea704b?w=500', rating=4.8, diet_type='Veg'),

            # Beverages
            FoodItem(name='Signature Gold Cocktail', description='A mix of premium spirits with edible gold flakes.', price=30.00, category='Beverages', image_url='https://images.unsplash.com/photo-1514362545857-3bc16c4c7d1b?w=500', rating=4.8, diet_type='Veg'),
            FoodItem(name='Sparkling Mango Mocktail', description='Refreshing blend of mango purée and sparkling water.', price=10.00, category='Beverages', image_url='https://images.unsplash.com/photo-1536935338788-846bb9981813?w=500', rating=4.6, diet_type='Veg'),
            FoodItem(name='Espresso Martini', description='A sophisticated blend of espresso and premium vodka.', price=18.00, category='Beverages', image_url='https://images.unsplash.com/photo-1621213340578-831620a5996f?w=500', rating=4.7, diet_type='Veg')
        ]
        db.session.add_all(mock_foods)
        
    db.session.commit()
    return "Database Initialized! <a href='/'>Go to Home</a>"

if __name__ == '__main__':
    app.run(debug=True, port=5000)
