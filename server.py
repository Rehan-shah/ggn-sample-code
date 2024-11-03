from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
import tensorflow as tf
from web3 import Web3
import json
import time
import threading

app = Flask(__name__)
CORS(app)

# Global model
model = tf.keras.Sequential([
    tf.keras.layers.Dense(10, input_shape=(784,), activation='relu'),
    tf.keras.layers.Dense(10, activation='softmax')
])
model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])

# Web3 setup
w3 = Web3(Web3.HTTPProvider('https://polygon-mumbai.infura.io/v3/YOUR_INFURA_PROJECT_ID'))
contract_address = 'YOUR_DEPLOYED_CONTRACT_ADDRESS'
contract_abi = json.loads('YOUR_CONTRACT_ABI')
contract = w3.eth.contract(address=contract_address, abi=contract_abi)

client_updates = {}
payment_queue = []
current_round = 0
min_clients_per_round = 3  

@app.route('/get-model', methods=['GET'])
def get_model():
    return jsonify({
        'weights': [w.tolist() for w in model.get_weights()],
        'round': current_round
    })

@app.route('/send-update', methods=['POST'])
def receive_update():
    global current_round
    client_update = request.json['update']
    client_round = request.json['round']
    client_address = request.json.get('clientAddress')

    if client_round != current_round:
        return jsonify({'status': 'error', 'message': 'Outdated round'})

    client_updates[client_address] = client_update

    payment_queue.append((client_address, time.time()))

    if len(client_updates) >= min_clients_per_round:
        aggregate_updates()
        current_round += 1

    return jsonify({'status': 'success', 'message': 'Update received and payment scheduled'})

def aggregate_updates():
    if not client_updates:
        return

    model_structure = [w.shape for w in model.get_weights()]

    aggregated_updates = [np.zeros(shape) for shape in model_structure]

    for update in client_updates.values():
        for i, layer_update in enumerate(update):
            aggregated_updates[i] += np.array(layer_update)

    num_clients = len(client_updates)
    aggregated_updates = [update / num_clients for update in aggregated_updates]

    current_weights = model.get_weights()
    updated_weights = [w + update for w, update in zip(current_weights, aggregated_updates)]
    model.set_weights(updated_weights)

    client_updates.clear()

def process_payments():
    while True:
        current_time = time.time()
        payments_to_process = [p for p in payment_queue if current_time - p[1] >= 3600]  # 1 hour = 3600 seconds

        for client_address, _ in payments_to_process:
            try:
                tx_hash = contract.functions.issuePayment(
                    client_address,
                    w3.toWei(0.1, 'ether')
                ).transact({'from': w3.eth.accounts[0]})
                print(f"Payment sent to {client_address}. Transaction hash: {tx_hash.hex()}")
            except Exception as e:
                print(f"Error processing payment for {client_address}: {str(e)}")

        payment_queue[:] = [p for p in payment_queue if p not in payments_to_process]

        time.sleep(60)  


payment_thread = threading.Thread(target=process_payments, daemon=True)
payment_thread.start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
