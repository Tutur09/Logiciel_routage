from flask import Flask, request, jsonify
import subprocess
import os

app = Flask(__name__)

@app.route('/run', methods=['POST'])
def run_script():
    try:
        # Récupérer le nom du script Python depuis la requête (optionnel)
        data = request.get_json()
        script_name = data.get("script_name", "script.py")

        # Vérifier si le fichier existe
        if not os.path.isfile(script_name):
            return jsonify({"error": f"Le fichier {script_name} n'existe pas."}), 400

        # Exécuter le script et capturer la sortie
        result = subprocess.run(
            ["python", script_name],  # Changez en "python3" si nécessaire
            capture_output=True,
            text=True,
        )
        
        # Retourner le résultat de l'exécution
        return jsonify({
            "output": result.stdout,
            "error": result.stderr,
            "returncode": result.returncode
        })
    except Exception as e:
        return jsonify({"error": f"Une erreur s'est produite : {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
