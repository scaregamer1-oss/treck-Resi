from flask import Flask, render_template, request, redirect, url_for, flash
import json
import os
import requests

app = Flask(__name__)
app.secret_key = 'kunci_rahasia_untuk_flash_message' # Ubah dengan string acak

# --- KONFIGURASI ---
API_KEY_BINDER = 'API_KEY_ANDA_DI_SINI' # Ganti dengan API Key Anda yang aman
DB_FILE = '/tmp/database.json'

# --- FUNGSI DATABASE ---
def load_db():
    if not os.path.exists(DB_FILE): return {"web_user": []}
    with open(DB_FILE, 'r') as f: 
        data = json.load(f)
        if "web_user" not in data:
            data["web_user"] = []
        return data

def save_db(data):
    with open(DB_FILE, 'w') as f: json.dump(data, f, indent=4)

# --- FUNGSI TRACKING ---
def track_resi_binder(kurir, resi, nama_barang="Tanpa Nama"):
    url = f"[https://api.binderbyte.com/v1/track?api_key=](https://api.binderbyte.com/v1/track?api_key=){API_KEY_BINDER}&courier={kurir.lower()}&awb={resi}"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        if data.get('status') == 200:
            d = data['data']
            history = d['history']
            
            history_text = []
            for i, h in enumerate(history[:3]): 
                history_text.append({"date": h['date'], "desc": h['desc']})
            
            return {"status": "success", "history": history_text}
        else:
            return {"status": "error", "message": data.get('message')}
    except Exception as e:
        return {"status": "error", "message": f"Gangguan API: {str(e)}"}

# --- ROUTING WEBSITE ---

# Halaman Utama (List Resi)
@app.route('/')
def index():
    db = load_db()
    resi_list = db["web_user"]
    
    # Ambil status tracking untuk setiap resi secara realtime saat halaman dimuat
    for item in resi_list:
        track_data = track_resi_binder(item['kurir'], item['resi'], item['nama'])
        item['track_data'] = track_data

    return render_template('index.html', resi_list=resi_list)

# Proses Tambah Resi
@app.route('/tambah', methods=['POST'])
def tambah():
    kurir = request.form.get('kurir').lower()
    resi = request.form.get('resi')
    nama = request.form.get('nama', 'Tanpa Nama')

    db = load_db()
    # Cek duplikasi
    if any(item['resi'] == resi for item in db["web_user"]):
        flash(f"Resi {resi} sudah terdaftar!", "warning")
    else:
        db["web_user"].append({'kurir': kurir, 'resi': resi, 'nama': nama})
        save_db(db)
        flash(f"Resi {resi} berhasil ditambahkan!", "success")
        
    return redirect(url_for('index'))

# Proses Hapus Resi
@app.route('/hapus/<resi>')
def hapus(resi):
    db = load_db()
    awal = len(db["web_user"])
    db["web_user"] = [i for i in db["web_user"] if i['resi'] != resi]
    
    if len(db["web_user"]) < awal:
        save_db(db)
        flash(f"Resi {resi} berhasil dihapus.", "success")
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
