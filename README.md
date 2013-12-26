# Torrent

I couldn't come up with a cooler name, so I'm sticking to "torrent" for now. 
Torrent is a pure-Python BitTorrent client written on top of 
[Tornado](http://www.tornadoweb.org/en/stable/), an asynchronous networking 
library.

## Features

 - Pure-Python. No libtorrent!
 - HTTP and UDP tracker support
 - Downloads files (works best for smaller ones)
 - Supports Python 2 and Python 3

## Broken Stuff

 - Little to no optimizations when writing pieces to disk
  - Tons of disk I/O
  - Eats up CPU while hashing
 - No optimistic unchoking
 - No support for multiple torrents
 - No µTP
 - No PEX
 - No DHT
 - No magnet links
 - `bittorrent.bencode` is incredibly slow
 - No cool UI

## Usage

Run the CLI frontend:

    user@hostname:~$ python -m bittorrent.client.cli --torrent=filename.torrent --path=/tmp/downloads
