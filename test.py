import argparse
import csv
import json
import threading
import time
from websocket import create_connection

# Globalna promjenljiva za kontrolu izvršavanja
running = True
# Inicijalizacija promjenljivih za čuvanje dodatnih statističkih podataka
stats_data_global = {
    'cpu_usage': 'unknown',
    'dl_sched_users_min': 'unknown',
    'dl_sched_users_max': 'unknown',
    'dl_sched_users_avg': 'unknown',
    'ul_sched_users_min': 'unknown',
    'ul_sched_users_max': 'unknown',
    'ul_sched_users_avg': 'unknown',
}

def listen_for_input():
    global running
    input("Press Enter to stop...\n")
    running = False

def websocket_thread(server_address):
    global stats_data_global
    ws = create_connection(f"ws://{server_address}")

    with open('output.csv', 'a', newline='') as csvfile:
        fieldnames = ['ran_ue_id', 'amf_ue_id', 'cqi', 'pusch_snr', 'epre', 'ul_path_loss', 'ri', 'initial_ta', 'p_ue', 'time', 'cpu_usage', 'dl_sched_users_min', 'dl_sched_users_max', 'dl_sched_users_avg', 'ul_sched_users_min', 'ul_sched_users_max', 'ul_sched_users_avg']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        if csvfile.tell() == 0:
            writer.writeheader()

        while running:
            try:
                # Obrada stats poruke i ažuriranje globalnih statističkih podataka
                ws.send(json.dumps({"message": "stats"}))
                result = ws.recv()
                stats_message = json.loads(result)
                # Ažuriranje globalnih statističkih podataka na osnovu odgovora
                update_global_stats(stats_message)

                # Slanje 'ue_get' poruke i obrada odgovora
                ue_get_message = {"message": "ue_get", "stats": True}
                ws.send(json.dumps(ue_get_message))
                result = ws.recv()
                if result:
                    message = json.loads(result)
                    if 'ue_list' in message:
                        current_time = message.get('time', 'unknown')
                        for ue in message['ue_list']:
                            for cell in ue['cells']:
                                row_data = {key: cell.get(key, 'unknown') for key in fieldnames[:-7] if key in cell}
                                row_data.update({
                                    'ran_ue_id': ue.get('ran_ue_id', 'unknown'),
                                    'amf_ue_id': ue.get('amf_ue_id', 'unknown'),
                                    'time': current_time,
                                    **stats_data_global  # Dodajemo ažurirane globalne statističke podatke
                                })
                                writer.writerow(row_data)

            except Exception as e:
                print(f"Error occurred: {e}")
                break

        ws.close()

def update_global_stats(stats_message):
    global stats_data_global
    if 'cells' in stats_message and '1' in stats_message['cells']:
        cell_data = stats_message['cells']['1']
        stats_data_global['cpu_usage'] = stats_message.get('cpu', {}).get('global', 'unknown')
        # Ekstrakcija i ažuriranje dodatnih statističkih podataka za ćeliju "1"
        stats_data_global.update({
            'dl_sched_users_min': cell_data.get('dl_sched_users_min', 'unknown'),
            'dl_sched_users_max': cell_data.get('dl_sched_users_max', 'unknown'),
            'dl_sched_users_avg': cell_data.get('dl_sched_users_avg', 'unknown'),
            'ul_sched_users_min': cell_data.get('ul_sched_users_min', 'unknown'),
            'ul_sched_users_max': cell_data.get('ul_sched_users_max', 'unknown'),
            'ul_sched_users_avg': cell_data.get('ul_sched_users_avg', 'unknown'),
        })

def main():
    parser = argparse.ArgumentParser(description="WebSocket remote API tool for collecting UE and CPU stats.")
    parser.add_argument("server", help="Server address for the WebSocket connection")
    args = parser.parse_args()

    ws_thread = threading.Thread(target=websocket_thread, args=(args.server,))
    ws_thread.start()

    listen_for_input()

    global running
    running = False
    ws_thread.join()

if __name__ == "__main__":
    main()