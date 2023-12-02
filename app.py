from flask import Flask, render_template,request
import subprocess
import platform
import time
import pandas as pd

app=Flask(__name__)

@app.route('/', methods=['GET','POST'])
def index():
    return render_template('index.html')

def run_commands_in_command_prompt(commands):
    if platform.system() == 'Windows':
        full_command = ' && '.join(commands)
        subprocess.Popen(['start', 'cmd', '/c', full_command], shell=True)
    else:
        pass

commands_set1 = [
    'cd "C:\\Users\\Msi\\Documents\\project\\intrusion detection system\\proj1"',
    'python server.py',
    'python server.py localhost 4444'
]

commands_set2 = [
    'cd "C:\\Users\\Msi\\Documents\\project\\intrusion detection system\\proj1"',
    'python client.py',
    'python client.py localhost 4444'
]

commands_set3 =[
    'cd "C:\\Users\\Msi\\Documents\\project\\intrusion detection system\\proj1"',
    'python analyzer.py',
    'python analyzer.py'
]

custom_sequence = [
    [commands_set1[0], commands_set2[0], commands_set3[0]],  # Run first commands of all sets
    [commands_set1[1], commands_set2[1], commands_set3[1]],  # Run second commands of all sets
    [commands_set1[2]],  # Run third command of set 1
    [commands_set2[2]],  # Run third command of set 2
    [commands_set3[2]]   # Run third command of set 3
]

for commands in custom_sequence:
    run_commands_in_command_prompt(commands)
    # Add a delay between opening command prompt windows if needed
    time.sleep(2)

@app.route('/data', methods=['GET','POST'])
def data():
    if request.method == 'POST':
        file=request.form['upload-file']
        #file_path='NETINFO -2023-11-30-Anshika-b-127.0.0.1-60395.csv'
        data= pd.read_csv(file)
        return render_template('data.html',data=data.to_html()) 

if __name__=='__main__':
    app.run(debug=True)       