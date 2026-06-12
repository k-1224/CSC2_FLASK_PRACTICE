import json
import datetime
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)

app.secret_key = 'save_the_seal'

def initialise_database():
    with sqlite3.connect('flower_shop.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number TEXT,
            customer_name TEXT, 
            items TEXT,
            addons TEXT,
            total REAL,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )              
        ''')
        conn.commit()

# ——— UTILITY FUNCTIONS ——— #
  # ——— DEFAULT ROUTE ——— #
@app.route('/')
def index():
    flowers, addons = load_data()
    cart = session.get ('cart', {})
    selected_addons = session.get ('selected_addons', {})
    total, flower_subtotal, addon_subtotal, discount_applied, subtotal, discount_amount = calculate_total(cart, selected_addons) 
    return render_template('index.html', flowers=flowers, addons=addons, cart=cart, total=total, selected_addons=selected_addons, 
                           flower_subtotal=flower_subtotal, addon_subtotal=addon_subtotal, 
                           discount_applied=discount_applied, subtotal=subtotal, discount_amount=discount_amount)

  # ——— UTILITY CALCULATE TOTAL ——— #
def calculate_total(cart, selected_addons):
    flower_subtotal = sum(item['price'] * item['quantity'] for item in cart.values())
    addon_subtotal = sum(item['price'] * item['quantity'] for item in selected_addons.values())

    subtotal = flower_subtotal + addon_subtotal

    discount_applied = False
    discount_amount = 0
    total = subtotal

    if subtotal > 180:
        discount_amount = subtotal * 0.1
        total = subtotal - discount_amount
        discount_applied = True

    return total, flower_subtotal, addon_subtotal, discount_applied, subtotal, discount_amount


def load_data ():
    with open('data/flowers.json') as file:
        flowers = json.load(file)
 
    with open('data/addons.json') as file:
        addons = json.load(file)
    
    return flowers, addons

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/orders')
def order_history():
    return render_template('order_history.html')

# ——— ROUTE AND FUNCTION ——— #
  # ——— FUNCTION CART ——— #
@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    flower = request.form['flower']
    quantity = int (request.form['quantity'])
    flowers, addons = load_data()
    cart = session.get('cart', {})

    if quantity >= 100:
        flash("You are ordering a lot! Consider calling us for a special deal.", "error")
        return redirect(url_for('index'))

    if flower not in flowers: 
        flash("Invalid flower selected.")
        return redirect(url_for('index.html'))
    
  
    if flower in cart: 
        cart[flower]['quantity'] += quantity
    else:
        cart[flower] = {
            'price': flowers[flower]['price'],
            'quantity': quantity
        }  

    print(session)  

    session['cart'] = cart 
    session.modified = True
    flash(f"{quantity} {flower}(s) added to cart.")   
    return redirect(url_for('index'))

  # ——— FUNCTION REMOVE CART ——— #
@app.route('/remove_from_cart/<item>')
def remove_from_cart(item):
    cart = session.get('cart', {})
  
    if item in cart:
        del cart[item]
        session['cart'] = cart
        session.modified = True
        flash(f"Removed all {item} from the cart.", "error")
    else:
        flash("Item not found in cart")

    return redirect(url_for('index'))

  # ——— FUNCTION ADDON ——— #
@app.route('/select_addon', methods=['POST'])
def select_addon():
    selected_addons = {}
    _, addons = load_data ()  
    selected_keys = request.form.getlist('addons')

    if not selected_keys:
        flash("Please select at least one add-on.", "error")
        return redirect(url_for('index'))

    for addon in selected_keys:
        if addon in addons:
            selected_addons[addon] = {
            'price': float(addons[addon]['price']), 
            'quantity': 1
            }

    session['selected_addons'] = selected_addons
    session.modified = True

    print(session)  
    flash(f"{len(selected_addons)} add-on(s) added to cart.")

    return redirect(url_for('index'))

  # ——— FUNCTION REMOVE ADDON ——— #
@app.route('/remove_from_selected_addons/<item>')
def remove_from_selected_addons(item):
    selected_addons = session.get('selected_addons', {})
  
    if item in selected_addons:
        del selected_addons[item]
        session['selected_addons'] = selected_addons
        session.modified = True
        flash(f"Removed all {item} from the add-on(s).", "error")
    else:
        flash("Item not found in add-on(s)", "error")

    return redirect(url_for('index'))

  # ——— FUNCTION CANCEL ORDER ——— #
@app.route('/cancel_order', methods=['POST'])
def cancel_order():
    session.pop('cart', None)
    session.pop('selected_addons', None)
    flash("Your order has been cancelled.", "error")  

    return redirect(url_for('index'))

  # ——— FUNCTION CHECKOUT ——— #
@app.route('/checkout', methods=['POST'])
def invoice():
    customer_name = request.form['customer_name'].strip().title()
  
    if not customer_name:
        flash("Customer name is required.")
        return(redirect(url_for('index')))
  
    cart = session.get('cart', {})
    selected_addons = session.get('selected_addons', {})

    if not cart:
        flash("Select flower to continue.", "error")
        return(redirect(url_for('index')))

    total, flower_subtotal, addon_subtotal, discount_applied, subtotal, discount_amount = calculate_total(cart, selected_addons)
    invoice_date = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    invoice_number = f"INV_{customer_name.replace(' ', '_')}_{invoice_date}"

    with sqlite3.connect('flower_shop.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO orders (invoice_number, customer_name, items, addons, total) 
        VALUES (?,?,?,?,?)              
        ''', (invoice_number, customer_name, json.dumps(cart), json.dumps(selected_addons), total))
        conn.commit()
    session.pop('cart', None)
    session.pop('selected_addons', None)

    invoice_filename = f"{invoice_number}.txt"

    print(f"\nSaved order for: {customer_name}")
    print(f"Cart: {cart}")
    print(f"Add-ons: {selected_addons}")
    print(f"Total: {total}\n")   

    with open(invoice_filename, "w") as f:
        f.write("---- Flower Shop Invoice ----\n\n")
        f.write(f"Invoice Number: {invoice_number}\n")
        f.write(f"Customer Name: {customer_name}\n")
        f.write(f"Date: {invoice_date}\n\n")

        f.write(f"Items:\n")
        for item, details in cart.items():
            f.write(f"-{item}: {details['quantity']} x  ${details['price']} = ${details['quantity'] * details['price']:.2f}\n")

        f.write("\n")
        f.write(f"Add-ons:\n")

        for item, details in selected_addons.items():
            f.write(f"-{item}: ${details['price']:.2f}\n")

        f.write("\n")
        f.write(f"Subtotal: ${subtotal:.2f}\n")
        f.write(f"Discount (10%): -${discount_amount}\n")
        f.write(f"Total: ${total:.2f}")

    return render_template('invoice.html', customer_name=customer_name, cart=cart, selected_addons=selected_addons, total=total, 
                           flower_subtotal=flower_subtotal, addon_subtotal=addon_subtotal, invoice_date=invoice_date, 
                           invoice_number=invoice_number, discount_applied=discount_applied, subtotal=subtotal, discount_amount=discount_amount) 

# ——— ALWAYS LAST CODE ——— #  
if __name__ == '__main__':
    initialise_database()
    app.run(debug=True)