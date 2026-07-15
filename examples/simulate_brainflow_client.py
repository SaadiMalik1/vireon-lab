import argparse
import time
import sys

# We'll mock the brainflow imports for now if they aren't available, but we expect to run this inside the venv
try:
    from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds
    from pylsl import StreamInfo, StreamOutlet
except ImportError:
    print("Please run this inside the virtual environment: source venv/bin/activate")
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="VIREON BrainFlow Client Test")
    parser.add_argument("--port", type=str, required=True, help="Virtual Cyton PTY port (e.g. /dev/pts/X)")
    parser.add_argument("--timeout", type=float, default=60.0, help="Timeout in seconds (0 to run forever)")
    args = parser.parse_args()

    # Configure BrainFlow to read from the Cyton Board
    params = BrainFlowInputParams()
    params.serial_port = args.port
    
    # 0 == Cyton 8 channel board
    board_id = BoardIds.CYTON_BOARD.value 
    
    board = None
    try:
        board = BoardShim(board_id, params)
        print(f"[BrainFlowClient] Connecting to Virtual Cyton on {args.port}...")
        board.prepare_session()
        
        # Start the stream
        board.start_stream()
        print("[BrainFlowClient] Stream started successfully.")
        
        # Setup LSL Outlet
        # Cyton has 8 EEG channels, 250 Hz
        info = StreamInfo('BrainFlowStream', 'EEG', 8, 250, 'float32', 'brainflow_cyton')
        outlet = StreamOutlet(info)
        print("[BrainFlowClient] LSL Outlet created.")
        
        packet_count = 0
        start_time = time.time()
        while args.timeout == 0 or time.time() - start_time < args.timeout:
            # Get the data from brainflow buffer
            data = board.get_board_data()
            if data.shape[1] > 0:
                # BrainFlow returns a 2D array [channels x samples]
                # The first few rows are package num, eeg data, etc.
                # For Cyton, EEG channels are rows 1 to 8.
                eeg_data = data[1:9, :]
                
                # Push to LSL (LSL expects [samples x channels] or just pushing chunk)
                # We need to transpose to [samples, channels]
                eeg_chunk = eeg_data.T.tolist()
                outlet.push_chunk(eeg_chunk)
                packet_count += data.shape[1]
                print(f"[BrainFlowClient] Parsed {packet_count} packets...", end='\r')
                
            time.sleep(0.05)
            
    except Exception as e:
        print(f"\n\n[BrainFlowClient] FATAL ERROR: BrainFlow crashed or lost synchronization!\nException: {e}")
        sys.exit(1)
        
    finally:
        try:
            if board and board.is_prepared():
                board.stop_stream()
                board.release_session()
        except Exception:
            pass

if __name__ == "__main__":
    main()
