from flask import Flask, render_template, request, redirect, url_for, flash
import json
import os
import requests

app = Flask(__name__)
app.secret_key = 'kunci_rahasia_untuk_flash_message'

# --- KONFIGURASI ---
API_KEY_BINDER = 'adaa0b5c137cce08aa928297268dc724096d004e955e632f5e863aae0d6a13de'
DB_FILE = '/tmp/database.json'

# --- FUNGSI DATABASE (DILENGKAPI ANTI-CRASH) ---
def load_db():
    if not os.path.exists(DB_FILE): 
        return {"web_user": []}
    
    try:
        with open(DB_FILE, 'r') as f: 
            data = json.load(f)
            if "web_user" not in data or not isinstance(data["web_user"], list):
                data["web_user"] = []
            return data
    except Exception:
        # Jika file json rusak/kosong (sering terjadi di Vercel /tmp), kembalikan list kosong
        return {"web_user": []}

def save_db(data):
    try:
        with open(DB_FILE, 'w') as f: 
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Gagal menyimpan database: {e}")

# --- FUNGSI TRACKING ---
def track_resi_binder(kurir, resi, nama_barang="Tanpa Nama"):
    # Pastikan kurir dan resi aman
    safe_kurir = str(kurir).strip().lower()
    safe_resi = str(resi).strip()
    
    url = f"https://api.binderbyte.com/v1/track?api_key={API_KEY_BINDER}&courier={safe_kurir}&awb={safe_resi}"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        if data.get('status') == 200:
            d = data.get('data', {})
            history = d.get('history', [])
            
            history_text = []
            for h in history[:3]: 
                history_text.append({"date": h.get('date', '-'), "desc": h.get('desc', '-')})
            
            return {"status": "success", "history": history_text}
        else:
            return {"status": "error", "message": data.get('message', 'Tidak diketahui')}
    except Exception as e:
        return {"status": "error", "message": f"Gangguan API: {str(e)}"}

# --- ROUTING WEBSITE ---

@app.route('/')
def index():
    try:
        db = load_db()
        resi_list = db.get("web_user", [])
        
        for item in resi_list:
            track_data = track_resi_binder(item.get('kurir', ''), item.get('resi', ''), item.get('nama', ''))
            item['track_data'] = track_data

        return render_template('index.html', resi_list=resi_list)
    except Exception as e:
        # Menampilkan error di layar jika terjadi masalah sistem, bukan blank 500
        return f"Terjadi kesalahan saat memuat halaman: {str(e)}"

@app.route('/tambah', methods=['POST'])
def tambah():
    try:
        kurir_raw = request.form.get('kurir')
        resi_raw = request.form.get('resi')
        
        # Cegah form kosong
        if not kurir_raw or not resi_raw:
            flash("Kurir dan Resi tidak boleh kosong!", "danger")
            return redirect(url_for('index'))

        kurir = kurir_raw.lower()
        resi = resi_raw.strip()
        nama = request.form.get('nama', 'Tanpa Nama')
        if not nama.strip():
            nama = 'Tanpa Nama'

        db = load_db()
        
        # Cek duplikasi
        if any(item.get('resi') == resi for item in db["web_user"]):
            flash(f"Resi {resi} sudah terdaftar!", "warning")
        else:
            db["web_user"].append({'kurir': kurir, 'resi': resi, 'nama': nama})
            save_db(db)
            flash(f"Resi {resi} berhasil ditambahkan!", "success")
            
    except Exception as e:
        flash(f"Gagal memproses data: {str(e)}", "danger")
        
    return redirect(url_for('index'))

@app.route('/hapus/<resi>')
def hapus(resi):
    try:
        db = load_db()
        awal = len(db["web_user"])
        db["web_user"] = [i for i in db["web_user"] if i.get('resi') != resi]
        
        if len(db["web_user"]) < awal:
            save_db(db)
            flash(f"Resi {resi} berhasil dihapus.", "success")
    except Exception as e:
        flash(f"Gagal menghapus resi: {str(e)}", "danger")
        
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
