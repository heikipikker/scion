// Copyright 2018 ETH Zurich
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//   http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package egress

import (
	"io"
	"net"
	"os"

	log "github.com/inconshreveable/log15"
	"github.com/prometheus/client_golang/prometheus"

	"github.com/scionproto/scion/go/lib/common"
	liblog "github.com/scionproto/scion/go/lib/log"
	"github.com/scionproto/scion/go/lib/ringbuf"
)

const (
	// FIXME(kormat): these relative sizes will fail if there are lots of egress dispatchers.
	egressFreePktsCap = 1024
	egressBufPkts     = 32

	ip4Ver    = 0x4
	ip6Ver    = 0x6
	ip4DstOff = 16
	ip6DstOff = 24
)

var egressFreePkts *ringbuf.Ring

func Init() {
	egressFreePkts = ringbuf.New(egressFreePktsCap, func() interface{} {
		return make(common.RawBytes, common.MaxMTU)
	}, "egress", prometheus.Labels{"ringId": "freePkts", "sessId": ""})
}

type Reader struct {
	log   log.Logger
	tunIO io.ReadWriteCloser
}

func NewReader(tunIO io.ReadWriteCloser) *Reader {
	return &Reader{log: log.New(), tunIO: tunIO}
}

func (r *Reader) Run() {
	defer liblog.LogPanicAndExit()
	r.log.Info("EgressReader: starting")
	bufs := make(ringbuf.EntryList, egressBufPkts)
BatchLoop:
	for {
		n, _ := egressFreePkts.Read(bufs, true)
		if n < 0 {
			break
		}
		for i := 0; i < n; i++ {
			buf := bufs[i].(common.RawBytes)
			bufs[i] = nil
			buf = buf[:cap(buf)]
			length, err := r.tunIO.Read(buf)
			if err != nil {
				if err == io.EOF {
					// TUN is closed, shut down reader.
					break BatchLoop
				}
				// Sometimes we don't receive a clean EOF, so we check if the
				// tunnel device is closed.
				if pErr, ok := err.(*os.PathError); ok {
					if pErr.Err == os.ErrClosed {
						break BatchLoop
					}
				}
				r.log.Error("EgressReader: error reading from TUN device", "err", err)
				continue
			}
			buf = buf[:length]
			dstIP, err := r.getDestIP(buf)
			if err != nil {
				// Release buffer back to free buffer pool
				egressFreePkts.Write(ringbuf.EntryList{buf}, true)
				// FIXME(kormat): replace with metric.
				r.log.Error("EgressReader: unable to get dest IP", "err", err)
				continue
			}
			dstIA, dstRing := NetMap.Lookup(dstIP)
			if dstRing == nil {
				// Release buffer back to free buffer pool
				egressFreePkts.Write(ringbuf.EntryList{buf}, true)
				// FIXME(kormat): replace with metric.
				r.log.Error("EgressReader: unable to find dest IA", "ip", dstIP)
				continue
			}
			if n, _ := dstRing.Write(ringbuf.EntryList{buf}, false); n != 1 {
				// Release buffer back to free buffer pool
				egressFreePkts.Write(ringbuf.EntryList{buf}, true)
				// FIXME(kormat): replace with metric.
				r.log.Error("EgressReader: no space in egress worker queue", "ia", dstIA)
			}
		}
	}
	r.log.Info("EgressDispatcher: stopping")
}

func (r *Reader) getDestIP(b common.RawBytes) (net.IP, error) {
	ver := (b[0] >> 4)
	switch ver {
	case ip4Ver:
		return net.IP(b[ip4DstOff : ip4DstOff+net.IPv4len]), nil
	case ip6Ver:
		return net.IP(b[ip6DstOff : ip6DstOff+net.IPv6len]), nil
	default:
		return nil, common.NewBasicError("Unsupported IP protocol version in egress packet", nil,
			"type", ver)
	}
}
