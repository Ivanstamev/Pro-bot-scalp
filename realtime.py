from flask_socketio import SocketIO
import threading
import time
import requests

price_feed = {
    'BTCUSDT': {'price': 43000, 'change': 2.3, 'volume': 1234567},
    'ETHUSDT': {'price': 2500, 'change': -1.2, 'volume': 987654},
    'SOLUSDT': {'price': 95, 'change': 4.5, 'volume': 456789}
}

class PriceFeed:
    def __init__(self):
        self.running = False
    
    def start(self):
        self.running = True
        thread = threading.Thread(target=self.stream)
        thread.daemon = True
        thread.start()
    
    def stream(self):
        while self.running:
            try:
                # РЎРёРјСѓР»РёСЂР°Р№ СЂРµР°Р»РЅРё С†РµРЅРё
                for symbol in price_feed:
                    price_feed[symbol]['price'] *= (1 + np.random.normal(0, 0.001))
                    price_feed[symbol]['change'] = np.random.normal(0, 2)
                
                # Emit to all connected clients
                from app import socketio
                socketio.emit('price_update', {
                    'symbol': 'BTCUSDT',
                    'price': price_feed['BTCUSDT']['price'],
                    'change': price_feed['BTCUSDT']['change']
                })
                time.sleep(2)
            except Exception as e:
                time.sleep(5)
