import express from 'express'
import swaggerUi from 'swagger-ui-express'
import yaml from 'yamljs'
import { createLibp2p } from 'libp2p'
import { createHelia } from 'helia'
import { createOrbitDB } from '@orbitdb/core'
import { LevelBlockstore } from 'blockstore-level'
import { tcp } from '@libp2p/tcp'
import { webSockets } from '@libp2p/websockets'
import { identify } from '@libp2p/identify'
import { mdns } from '@libp2p/mdns'
import { gossipsub } from '@chainsafe/libp2p-gossipsub'
import { noise } from '@chainsafe/libp2p-noise'
import { yamux } from '@chainsafe/libp2p-yamux'

// Use top-level await instead of async IIFE

const TCP_PORT  = Number(process.env.HELIA_TCP_PORT || 4101)
const WS_PORT   = Number(process.env.HELIA_WS_PORT  || 4102)
const DB_NAME   = process.env.ORBIT_DB_NAME || 'qoe-log'
const HTTP_PORT = Number(process.env.ORBIT_HTTP_PORT || 3110)

// Persistent storage
const blockstore = new LevelBlockstore('/data/orbitdb/ipfs/blocks')
await blockstore.open()

const libp2p = await createLibp2p({
    peerDiscovery: [mdns()],
    addresses: {
      listen: [
        `/ip4/0.0.0.0/tcp/${TCP_PORT}`,
        `/ip4/0.0.0.0/tcp/${WS_PORT}/ws`
      ]
    },
    transports: [tcp(), webSockets()],
    connectionEncrypters: [noise()],
    streamMuxers: [yamux()],
    services: {
      identify: identify(),
      pubsub: gossipsub({ allowPublishToZeroTopicPeers: true })
    }
  })

const ipfs = await createHelia({ libp2p, blockstore })
const orbitdb = await createOrbitDB({ ipfs })

// Use a documents DB so we can do structured queries
// Each record must have an `_id` field (our composite key).
const db = await orbitdb.open(DB_NAME, { type: 'documents', indexBy: '_id' })

console.log('OrbitDB running')
console.log('DB address:', db.address)
console.log('Libp2p addrs:', orbitdb.ipfs.libp2p.getMultiaddrs())

// -------------------- HTTP gateway --------------------

const app = express()
app.use(express.json({ limit: '5mb' }))

  // Swagger/OpenAPI setup (external YAML)
  const swaggerSpec = yaml.load('./swagger.yaml')
  app.use('/api-docs', swaggerUi.serve, swaggerUi.setup(swaggerSpec))

  app.get('/health', (req, res) => {
    res.json({
      ok: true,
      db: DB_NAME,
      address: db.address,
      libp2p: orbitdb.ipfs.libp2p.getMultiaddrs().map(a => a.toString())
    })
  })

  function toIsoOrNull(v) {
    if (!v) return null
    const d = new Date(v)
    if (Number.isNaN(d.getTime())) return null
    return d.toISOString()
  }

  function makeRunId({ buildingId, start, end, modelVersion }) {
    return `${buildingId}|${start}|${end}|${modelVersion || 'v1'}`
  }

  app.post('/runs', async (req, res) => {
    try {
      const buildingId = req.body?.buildingId
      const start = toIsoOrNull(req.body?.start)
      const end = toIsoOrNull(req.body?.end)
      const modelVersion = req.body?.modelVersion || 'v1'

      if (!buildingId || !start || !end) {
        return res.status(400).json({ ok: false, error: 'buildingId, start, end are required (valid dates).' })
      }
      if (!req.body?.inputHash || !req.body?.outputHash) {
        return res.status(400).json({ ok: false, error: 'inputHash and outputHash are required.' })
      }

      const _id = makeRunId({ buildingId, start, end, modelVersion })

      const doc = {
        _id,
        buildingId,
        start,
        end,
        modelVersion,
        inputHash: req.body.inputHash,
        outputHash: req.body.outputHash,
        sensorsHash: req.body.sensorsHash || null,
        weatherHash: req.body.weatherHash || null,
        modelHash: req.body.modelHash || null,
        createdAt: new Date().toISOString()
      }

      await db.put(doc)
      res.json({ ok: true, _id })
    } catch (e) {
      res.status(500).json({ ok: false, error: String(e?.message || e) })
    }
  })

  app.get('/runs', async (req, res) => {
    try {
      const buildingId = req.query?.buildingId
      const start = toIsoOrNull(req.query?.start)
      const end = toIsoOrNull(req.query?.end)
      const modelVersion = req.query?.modelVersion

      if (!buildingId || !start || !end) {
        return res.status(400).json({ ok: false, error: 'buildingId, start, end query params are required (valid dates).' })
      }

      const items = await db.query(d => {
        if (d.buildingId !== buildingId) return false
        if (modelVersion && d.modelVersion !== modelVersion) return false
        // overlap rule: [d.start, d.end] overlaps [start, end]
        return !(d.end < start || d.start > end)
      })

      // sort ascending by start
      items.sort((a, b) => {
        if (a.start < b.start) return -1;
        if (a.start > b.start) return 1;
        return 0;
      })

      res.json({ ok: true, count: items.length, items })
    } catch (e) {
      res.status(500).json({ ok: false, error: String(e?.message || e) })
    }
  })

  app.get('/runs/:id', async (req, res) => {
    try {
      const _id = req.params.id
      const doc = await db.get(_id)
      if (!doc) return res.status(404).json({ ok: false, error: 'Not found' })
      res.json({ ok: true, item: doc })
    } catch (e) {
      res.status(500).json({ ok: false, error: String(e?.message || e) })
    }
  })

app.listen(HTTP_PORT, '0.0.0.0', () => {
  console.log(`OrbitDB HTTP gateway listening on :${HTTP_PORT}`)
})
process.stdin.resume()
