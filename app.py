from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
from datetime import datetime
import pandas as pd
import numpy as np
import talib
from models import db, Trade, Balance, Config
from realtime import price_feed
from security import api_key_required, rate_limit_trading
from strategies import STRATEGIES, generate_signal
from utils import save_screenshot, calculate_position_size, calculate_win_rate

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'super-secret-dev-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///trading_bot.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')
limiter = Limiter(app, key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])

with app.app_context():
    db.create_all()
    if not Balance.query.first():
        db.session.add(Balance(balance=10000, equity=10000))
        db.session.commit()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health')
def health():
    latest_balance = Balance.query.order_by(Balance.timestamp.desc()).first()
    return jsonify({
        "status": "healthy", 
        "version": "1.0.0",
        "trades": Trade.query.count(),
        "balance": getattr(latest_balance, 'equity', 10000),
        "timestamp": datetime.utcnow().isoformat()
    })

@app.route('/api/live')
def live_data():
    latest_balance = Balance.query.order_by(Balance.timestamp.desc()).first()
    open_trades = Trade.query.filter_by(status='open').count()
    win_rate = calculate_win_rate()
    return jsonify({
        'balance': getattr(latest_balance, 'equity', 10000),
        'open_trades': open_trades,
        'win_rate': win_rate,
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/api/trades')
def get_trades():
    trades = Trade.query.order_by(Trade.timestamp.desc()).limit(100).all()
    return jsonify([t.__dict__ for t in trades])

@app.route('/api/strategies')
def get_strategies():
    return jsonify(STRATEGIES)

@app.route('/api/trade', methods=['POST'])
@api_key_required
@rate_limit_trading
def execute_trade():
    data = request.json
    signal = generate_signal(data)
    
    size = calculate_position_size(data.get('balance', 10000), signal)
    
    trade = Trade(
        symbol=data['symbol'],
        side=signal['signal'].lower(),
        entry_price=float(data['price']),
        quantity=size,
        strategy=data.get('strategy', 'manual')
    )
    trade.screenshot_url = save_screenshot(data['symbol'], data['price'])
    db.session.add(trade)
    db.session.commit()
    
    socketio.emit('new_trade', trade.__dict__)
    return jsonify(signal)

@socketio.on('connect')
def handle_connect():
    emit('status', {'msg': 'Connected to Trading Bot'})

@socketio.on('get_history')
def handle_history(data):
    trades = Trade.query.order_by(Trade.timestamp.desc()).limit(50).all()
    emit('trade_history', [t.__dict__ for t in trades])

if __name__ == '__main__':
    price_feed.start()
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
