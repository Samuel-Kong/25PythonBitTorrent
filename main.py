import bencodepy
import asyncio
import socket
import hashlib
import os
import struct
import requests
import random
from hashlib import sha1
from fastapi import FastAPI

# constants
PIECE_SIZE = 16384  # size of each piece in bytes

# function to parse the .torrent file
def parse_torrent(file_path):
    with open(file_path, 'rb') as f:
        torrent_data = bencodepy.decode(f.read())
    return torrent_data

# function to connect to the tracker and get peer list
def get_peers(tracker_url, torrent_data):
    params = {
        'info_hash': sha1(bencodepy.encode(torrent_data['info'])).digest(),
        'peer_id': b'-PY0001-' + bytes([random.randint(0, 255) for _ in range(12)]),
        'port': 6881,
        'uploaded': 0,
        'downloaded': 0,
        'left': torrent_data['info']['length'],
        'event': 'started',
    }
    # send request to tracker and get peers
    response = requests.get(tracker_url, params=params)
    tracker_response = bencodepy.decode(response.content)
    peers = tracker_response.get('peers', [])
    return peers

# async function to handle peer connection
async def connect_to_peer(peer, torrent_data):
    peer_ip = socket.inet_ntoa(peer[:4])  # convert peer IP from bytes to string
    peer_port = struct.unpack('>H', peer[4:6])[0]  # extract peer port
    print(f"connecting to {peer_ip}:{peer_port}")
    
    # create socket and connect to peer
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((peer_ip, peer_port))
    
    # send handshake
    handshake = b'\x13BITTORRENT protocol' + b'\x00' * 8 + sha1(bencodepy.encode(torrent_data['info'])).digest() + b'-PY0001-' 
    sock.send(handshake)
    
    # receive response from peer
    response = sock.recv(68)
    if response[:20] == b'\x13BITTORRENT protocol':
        print(f"handshake with {peer_ip}:{peer_port} successful!")
    else:
        print(f"failed handshake with {peer_ip}:{peer_port}")
        sock.close()
        return None
    
    return sock

# async function to request a piece from a peer
async def request_piece(sock, piece_index, torrent_data):
    piece_hash = sha1(piece_index.to_bytes(4, 'big')).digest()  # generate piece hash
    request = struct.pack('>I', 13) + b'\x06' + struct.pack('>I', piece_index) + struct.pack('>I', 0)  # request message
    sock.send(request)
    
    # receive piece data from peer
    piece_data = sock.recv(PIECE_SIZE)
    if piece_data:
        print(f"received piece {piece_index}")
        return piece_data
    return None

# function to verify downloaded pieces
def verify_piece(piece_index, piece_data, torrent_data):
    expected_hash = sha1(piece_index.to_bytes(4, 'big')).digest()  # expected piece hash
    if sha1(piece_data).digest() == expected_hash:
        print(f"piece {piece_index} verified successfully.")
        return True
    else:
        print(f"piece {piece_index} failed verification.")
        return False

# function to save the downloaded pieces to disk
def save_piece(piece_index, piece_data, file_path):
    with open(file_path, 'r+b') as f:
        f.seek(piece_index * PIECE_SIZE)  # move to correct position in file
        f.write(piece_data)
    print(f"saved piece {piece_index}")

# async function to download the file
async def download_file(peers, torrent_data, file_path):
    # prepare the file by truncating to correct size
    file_size = torrent_data['info']['length']
    total_pieces = (file_size // PIECE_SIZE) + (1 if file_size % PIECE_SIZE != 0 else 0)
    with open(file_path, 'wb') as f:
        f.truncate(file_size)

    # loop through peers and download pieces
    for peer in peers:
        sock = await connect_to_peer(peer, torrent_data)
        if sock is None:
            continue
        
        # download pieces from this peer
        for piece_index in range(total_pieces):
            piece_data = await request_piece(sock, piece_index, torrent_data)
            if piece_data and verify_piece(piece_index, piece_data, torrent_data):
                save_piece(piece_index, piece_data, file_path)
        
        sock.close()

# FastAPI setup to run server and interact with the client
app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "BitTorrent Client is Running!"}

# function to run the BitTorrent client
def run_bittorrent_client(torrent_file, output_file):
    torrent_data = parse_torrent(torrent_file)
    tracker_url = torrent_data['announce']  # get tracker URL
    peers = get_peers(tracker_url, torrent_data)  # get peers from tracker
    print(f"found peers: {peers}")
    
    asyncio.run(download_file(peers, torrent_data, output_file))  # start downloading

# main entry point
if __name__ == "__main__":
    import uvicorn
    
    # set paths for torrent file and output file
    torrent_file = 'path_to_your_torrent_file.torrent'  # replace with your .torrent file path
    output_file = 'downloaded_file'  # replace with your output file path
    
    # run the BitTorrent client
    run_bittorrent_client(torrent_file, output_file)
    
    # run FastAPI server to interact with the client
    uvicorn.run(app, host="0.0.0.0", port=8000)
