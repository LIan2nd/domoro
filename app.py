from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime
from pymongo import MongoClient
from math import ceil
from collections import defaultdict

client = MongoClient('mongodb+srv://Lroot:blokk@fullstacklearningx.p4dqs.mongodb.net/?retryWrites=true&w=majority&appName=fullstackLearningX')
db = client.dbdomoro

app = Flask(__name__)

def format_rupiah(amount):
    """
    Memformat angka menjadi format Rupiah.
    Contoh: 1000000 -> 'Rp 1.000.000,00'
    """
    return f"{amount:,.2f}".replace(',', '.').replace('.', '.', 1)

app.jinja_env.filters['rupiah'] = format_rupiah

# Route untuk halaman utama
@app.route('/')
def index():
    # Mendapatkan data dari query string untuk filter dan pagination
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    transaction_type = request.args.get('type', '')
    per_page = int(request.args.get('per_page', 10))  # Default 10 data per halaman
    page = int(request.args.get('page', 1))

    # Filter query untuk transaksi
    query = {}
    if start_date:
        query['date'] = {'$gte': start_date}
    if end_date:
        if 'date' not in query:
            query['date'] = {}
        query['date']['$lte'] = end_date
    if transaction_type:
        query['type'] = transaction_type
    
    # Hitung total transaksi sesuai query
    total_transactions = db.transactions.count_documents(query)
    total_pages = ceil(total_transactions / per_page)
    
    # Ambil data transaksi berdasarkan filter dan pagination
    transactions_cursor = db.transactions.find(query).sort('date', -1).skip((page - 1) * per_page).limit(per_page)
    transactions = list(transactions_cursor)

    # Menghitung total debit dan kredit per hari dari semua transaksi
    daily_totals = {}
    all_transactions = db.transactions.find(query).sort('date', -1)  # Ambil semua transaksi sesuai filter
    for transaction in all_transactions:
        date = transaction['date'].split(' ')[0]  # Ambil hanya tanggal tanpa jam
        if date not in daily_totals:
            daily_totals[date] = {'debit': 0, 'credit': 0}
        if transaction['type'] == 'debit':
            daily_totals[date]['debit'] += transaction['amount']
        else:
            daily_totals[date]['credit'] += transaction['amount']
    
    for date, totals in daily_totals.items():
        daily_totals[date]['net'] = totals['debit'] - totals['credit']

    # Menghitung total debit, kredit, dan net per bulan
    monthly_totals = defaultdict(lambda: {'debit': 0, 'credit': 0, 'net': 0})
    for transaction in all_transactions:
        # Ambil tahun dan bulan dari transaksi
        month = datetime.strptime(transaction['date'], '%Y-%m-%d %H:%M:%S').strftime('%Y-%m')
        if transaction['type'] == 'debit':
            monthly_totals[month]['debit'] += transaction['amount']
        else:
            monthly_totals[month]['credit'] += transaction['amount']
    
    for month, totals in monthly_totals.items():
        totals['net'] = totals['debit'] - totals['credit']

    return render_template(
        'index.html',
        transactions=transactions,
        daily_totals=daily_totals,
        monthly_totals=monthly_totals,
        start_date=start_date,
        end_date=end_date,
        type=transaction_type,
        per_page=per_page,
        total_pages=total_pages,
        current_page=page
    )

# Route untuk menambah transaksi baru
@app.route('/add', methods=['GET', 'POST'])
def add_transaction():
    if request.method == 'POST':
        # Mendapatkan data dari form
        date = request.form['date']
        description = request.form['description']
        amount = float(request.form['amount'])
        type = request.form['type']
        
        # Menyimpan transaksi ke MongoDB
        db.transactions.insert_one({
            'date': date,
            'description': description,
            'amount': amount,
            'type': type
        })
        
        return redirect(url_for('index'))
    
    return render_template('add_transaction.html', datetime=datetime)

port = 5000
debug = True
if __name__ == "__main__": 
    app.run('0.0.0.0', port=port, debug=debug)
