var express = require('express'),
    async = require('async'),
    { Pool } = require('pg'),
    cookieParser = require('cookie-parser'),
    path = require('path'),
    redis = require('redis'),
    app = express(),
    server = require('http').Server(app),
    io = require('socket.io')(server);

var port = process.env.RESULT_PORT || process.env.PORT || 4000;

// Database Configuration from environment
var dbHost = process.env.DB_HOST || 'db';
var dbPort = process.env.DB_PORT || 5432;
var dbName = process.env.DB_NAME || 'postgres';
var dbUser = process.env.POSTGRES_USER || 'postgres';
var dbPassword = process.env.POSTGRES_PASSWORD || 'postgres';

// Redis Configuration
var redisHost = process.env.REDIS_HOST || 'redis';
var redisPort = process.env.REDIS_PORT || 6379;

var connectionString = `postgres://${dbUser}:${dbPassword}@${dbHost}:${dbPort}/${dbName}`;

// Create Redis subscriber for vote updates
var redisSubscriber = redis.createClient({
  host: redisHost,
  port: redisPort
});

redisSubscriber.on('error', function(err) {
  console.error('Redis subscriber error:', err);
});

redisSubscriber.on('connect', function() {
  console.log('Connected to Redis for vote updates');
});

io.on('connection', function (socket) {

  socket.emit('message', { text : 'Welcome!' });

  socket.on('subscribe', function (data) {
    socket.join(data.channel);
  });
});

var pool = new Pool({
  connectionString: connectionString
});

async.retry(
  {times: 1000, interval: 1000},
  function(callback) {
    pool.connect(function(err, client, done) {
      if (err) {
        console.error("Waiting for db");
      }
      callback(err, client);
    });
  },
  function(err, client) {
    if (err) {
      return console.error("Giving up");
    }
    console.log("Connected to db");
    
    // Initial load
    getVotes(client);
    
    // Subscribe to Redis vote_updates channel
    redisSubscriber.subscribe('vote_updates');
    redisSubscriber.on('message', function(channel, message) {
      if (channel === 'vote_updates') {
        console.log('Vote update received, refreshing scores...');
        getVotes(client);
      }
    });
  }
);

function getVotes(client) {
  // Get all competitions with their vote counts
  client.query(`
    SELECT 
      c.id,
      c.name,
      c.description,
      c.option_a,
      c.option_b,
      c.status,
      COUNT(CASE WHEN v.vote = 'a' THEN 1 END) as votes_a,
      COUNT(CASE WHEN v.vote = 'b' THEN 1 END) as votes_b
    FROM competitions c
    LEFT JOIN votes v ON c.id = v.competition_id
    GROUP BY c.id, c.name, c.description, c.option_a, c.option_b, c.status
    ORDER BY c.created_at DESC
  `, [], function(err, result) {
    if (err) {
      console.error("Error performing query: " + err);
    } else {
      var competitions = formatCompetitions(result);
      io.sockets.emit("scores", JSON.stringify(competitions));
    }
    
    // No more setTimeout - only updates on Redis pub/sub events
  });
}

function formatCompetitions(result) {
  var competitions = [];

  result.rows.forEach(function (row) {
    competitions.push({
      id: row.id,
      name: row.name,
      description: row.description,
      option_a: row.option_a,
      option_b: row.option_b,
      status: row.status,
      a: parseInt(row.votes_a || 0),
      b: parseInt(row.votes_b || 0)
    });
  });

  return competitions;
}

function collectVotesFromResult(result) {
  var votes = {a: 0, b: 0};

  result.rows.forEach(function (row) {
    votes[row.vote] = parseInt(row.count);
  });

  return votes;
}

app.use(cookieParser());
app.use(express.urlencoded());
app.use(express.static(__dirname + '/views'));

app.get('/', function (req, res) {
  res.sendFile(path.resolve(__dirname + '/views/index.html'));
});

app.get('/health', function (_req, res) {
  res.json({ status: 'ok' });
});

app.get('/ready', async function (_req, res) {
  try {
    await pool.query('SELECT 1');
    res.json({ status: 'ready' });
  } catch (err) {
    console.error('Readiness check failed', err);
    res.status(503).json({ status: 'error', reason: 'db_unavailable' });
  }
});

app.get('/api/scores', async function (_req, res) {
  try {
    const result = await pool.query(`
      SELECT 
        c.id,
        c.name,
        c.description,
        c.option_a,
        c.option_b,
        c.status,
        COUNT(CASE WHEN v.vote = 'a' THEN 1 END) as votes_a,
        COUNT(CASE WHEN v.vote = 'b' THEN 1 END) as votes_b
      FROM competitions c
      LEFT JOIN votes v ON c.id = v.competition_id
      GROUP BY c.id, c.name, c.description, c.option_a, c.option_b, c.status
      ORDER BY c.created_at DESC
    `);
    
    const competitions = formatCompetitions(result);
    res.json(competitions);
  } catch (err) {
    console.error('Error fetching scores:', err);
    res.json([]);
  }
});

server.listen(port, function () {
  var port = server.address().port;
  console.log('App running on port ' + port);
});
