import json

from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)

app.secret_key = 'save_the_seal'

#UTILITY FUNCTIONS
  #DEFAULT ROUTE
@app.route('/')
def index():
  flowers, addons = load_data()
  cart = session.get ('cart', {})
  total = calculate_total(cart)
  return render_template('index.html', flowers=flowers, addons=addons, cart=cart, total=total)

def calculate_total(cart):
  total = sum(item['price'] * item ['quantity'] for item in cart.values())
  return total

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

@app.route('/checkout')
def invoice():
  return render_template('invoice.html')

#ROUTE AND FUNCTION
@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
  flower = request.form['flower']
  quantity = int (request.form['quantity'])
  flowers, addons = load_data()
  cart = session.get('cart', {})

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

  session['cart'] = cart 
  session.modified = True
  flash(f"{quantity} {flower}(s) added to cart.")   
  return redirect(url_for('index'))

@app.route('/remove_from_cart/<item>')
def remove_from_cart(item):
  cart = session.get('cart', {})
  
  if item in cart:
    del cart[item.capitalize()]
    session['cart'] = cart
    session.modified = True
    flash(f"Removed all {item} from the cart.")
  else:
    flash("Item not found in cart")

  return redirect(url_for('index'))

#MUST BE THE LAST CODE
if __name__ == '__main__':
  app.run(debug=True)