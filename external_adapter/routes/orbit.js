/**
 * orbit.js - OrbitDB Documents DB (Helia stack)
 *
 * Requires:
 *   npm i @orbitdb/core helia libp2p
 *   npm i @libp2p/tcp @libp2p/websockets
 *   npm i @chainsafe/libp2p-noise @chainsafe/libp2p-yamux @chainsafe/libp2p-gossipsub
 *   npm i @libp2p/identify
 *
 * Node 20+ required.
 */

"use strict";

const express = require("express");
const path = require("node:path");
require("dotenv").config({ path: path.resolve(__dirname, "..", ".env") });

const router = express.Router();
router.use(express.json({ limit: "5mb" }));

const ORBITDB_DIRECTORY = process.env.ORBITDB_DIRECTORY || "./orbitdb";
const ORBITDB_DBNAME = process.env.ORBITDB_DBNAME || "hash_catalog";

let _orbitdb = null;
let _db = null;

const s = (x) => (typeof x === "string" ? x.trim() : x);
const addrToString = (a) =>
  a && typeof a.toString === "function" ? a.toString() : String(a);

/* -------------------------------------------------------------------------- */
/*                               INIT ORBITDB                                 */
/* -------------------------------------------------------------------------- */

async function getOrbitDB() {
  if (_orbitdb) return _orbitdb;

  const [{ createLibp2p }, { createHelia }, { createOrbitDB }] =
    await Promise.all([
      import("libp2p"),
      import("helia"),
      import("@orbitdb/core"),
    ]);

  const { tcp } = await import("@libp2p/tcp");
  const { webSockets } = await import("@libp2p/websockets");
  const { noise } = await import("@chainsafe/libp2p-noise");
  const { yamux } = await import("@chainsafe/libp2p-yamux");
  const { gossipsub } = await import("@chainsafe/libp2p-gossipsub");
  const { identify } = await import("@libp2p/identify");

  const libp2p = await createLibp2p({
    transports: [tcp(), webSockets()],
    connectionEncryption: [noise()],
    streamMuxers: [yamux()],
    services: {
      identify: identify(),
      pubsub: gossipsub(),
    },
  });

  const ipfs = await createHelia({ libp2p });

  _orbitdb = await createOrbitDB({
    ipfs,
    directory: ORBITDB_DIRECTORY,
  });

  return _orbitdb;
}

async function getDocumentsDb(dbname = ORBITDB_DBNAME) {
  if (_db && _db.__dbname === dbname) return _db;

  const orbitdb = await getOrbitDB();

  const db = await orbitdb.open(dbname, {
    type: "documents",
    indexBy: "_id",
  });

  if (typeof db.load === "function") await db.load();

  db.__dbname = dbname;
  _db = db;

  return db;
}

/* -------------------------------------------------------------------------- */
/*                               SWAGGER BLOCKS                               */
/* -------------------------------------------------------------------------- */

/**
 * @swagger
 * tags:
 *   - name: Orbit
 *     description: OrbitDB per-building window metadata storage.
 *
 * components:
 *   schemas:
 *     OrbitWindowItem:
 *       type: object
 *       required: [buildingId, start, end, dataHash, cid]
 *       properties:
 *         _id:
 *           type: string
 *           readOnly: true
 *           description: Derived by server as buildingId|start|end
 *         buildingId:
 *           type: string
 *         start:
 *           type: string
 *           format: date-time
 *         end:
 *           type: string
 *           format: date-time
 *         dataHash:
 *           type: string
 *         forecastHash:
 *           type: string
 *           nullable: true
 *         cid:
 *           type: string
 *
 *     OrbitStoreRequest:
 *       type: object
 *       required: [items]
 *       properties:
 *         db:
 *           type: string
 *         items:
 *           type: array
 *           items:
 *             $ref: '#/components/schemas/OrbitWindowItem'
 *
 *     OrbitStoreResponse:
 *       type: object
 *       properties:
 *         ok:
 *           type: boolean
 *         db:
 *           type: string
 *         stored:
 *           type: integer
 *         ids:
 *           type: array
 *           items:
 *             type: string
 *         heads:
 *           type: array
 *           items:
 *             type: string
 *
 *     ErrorResponse:
 *       type: object
 *       properties:
 *         ok:
 *           type: boolean
 *         error:
 *           type: string
 */

/**
 * @swagger
 * /orbit/store:
 *   post:
 *     summary: Store building window metadata
 *     tags: [Orbit]
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             $ref: '#/components/schemas/OrbitStoreRequest'
 *     responses:
 *       200:
 *         description: Stored
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/OrbitStoreResponse'
 *       400:
 *         description: Invalid input
 *       500:
 *         description: Server error
 */
router.post("/store", async (req, res) => {
  try {
    const dbname = s(req.body.db) || ORBITDB_DBNAME;
    const items = req.body.items;

    if (!Array.isArray(items) || items.length === 0) {
      return res.status(400).json({ ok: false, error: "items[] required" });
    }

    const db = await getDocumentsDb(dbname);

    const heads = [];
    const ids = [];

    for (const raw of items) {
      const buildingId = s(raw.buildingId);
      const start = s(raw.start);
      const end = s(raw.end);
      const dataHash = s(raw.dataHash);
      const cid = s(raw.cid);

      if (!buildingId || !start || !end || !dataHash || !cid) {
        return res.status(400).json({
          ok: false,
          error: "Missing required fields",
        });
      }

      const _id = `${buildingId}|${start}|${end}`;

      const doc = { ...raw, _id };

      const head = await db.put(doc);

      heads.push(head);
      ids.push(_id);
    }

    return res.json({
      ok: true,
      db: addrToString(db.address),
      stored: items.length,
      ids,
      heads,
    });
  } catch (err) {
    return res.status(500).json({
      ok: false,
      error: err.message,
    });
  }
});

/**
 * @swagger
 * /orbit/health:
 *   get:
 *     summary: OrbitDB health check
 *     tags: [Orbit]
 */
router.get("/health", async (req, res) => {
  try {
    const db = await getDocumentsDb();
    return res.json({
      ok: true,
      db: addrToString(db.address),
    });
  } catch (err) {
    return res.status(500).json({ ok: false, error: err.message });
  }
});

module.exports = router;
