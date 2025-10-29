using System;
using System.Data.Common;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Threading;
using Newtonsoft.Json;
using Npgsql;
using StackExchange.Redis;

namespace Worker
{
    public class Program
    {
        public static int Main(string[] args)
        {
            try
            {
                // Configuration from environment variables
                var dbHost = Environment.GetEnvironmentVariable("DB_HOST") ?? "db";
                var dbPort = Environment.GetEnvironmentVariable("DB_PORT") ?? "5432";
                var dbName = Environment.GetEnvironmentVariable("DB_NAME") ?? "postgres";
                var dbUser = Environment.GetEnvironmentVariable("POSTGRES_USER") ?? "postgres";
                var dbPassword = Environment.GetEnvironmentVariable("POSTGRES_PASSWORD") ?? "postgres";
                var redisHost = Environment.GetEnvironmentVariable("REDIS_HOST") ?? "redis";

                var connectionString = $"Server={dbHost};Port={dbPort};Database={dbName};Username={dbUser};Password={dbPassword};";

                var pgsql = OpenDbConnection(connectionString);
                var redisConn = OpenRedisConnection(redisHost);
                var redis = redisConn.GetDatabase();

                // Keep alive is not implemented in Npgsql yet. This workaround was recommended:
                // https://github.com/npgsql/npgsql/issues/1214#issuecomment-235828359
                var keepAliveCommand = pgsql.CreateCommand();
                keepAliveCommand.CommandText = "SELECT 1";

                var definition = new { vote = "", voter_id = "", competition_id = 0, user_id = 0 };
                while (true)
                {
                    // Slow down to prevent CPU spike, only query each 100ms
                    Thread.Sleep(100);

                    // Reconnect redis if down
                    if (redisConn == null || !redisConn.IsConnected) {
                        Console.WriteLine("Reconnecting Redis");
                        redisConn = OpenRedisConnection("redis");
                        redis = redisConn.GetDatabase();
                    }
                    string json = redis.ListLeftPopAsync("votes").Result;
                    if (json != null)
                    {
                        var vote = JsonConvert.DeserializeAnonymousType(json, definition);
                        Console.WriteLine($"Processing vote for '{vote.vote}' by '{vote.voter_id}' in competition {vote.competition_id}");
                        // Reconnect DB if down
                        if (!pgsql.State.Equals(System.Data.ConnectionState.Open))
                        {
                            Console.WriteLine("Reconnecting DB");
                            pgsql = OpenDbConnection(connectionString);
                        }
                        else
                        { // Normal +1 vote requested
                            UpdateVote(pgsql, vote.voter_id, vote.vote, vote.competition_id, vote.user_id);
                        }
                    }
                    else
                    {
                        keepAliveCommand.ExecuteNonQuery();
                    }
                }
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine(ex.ToString());
                return 1;
            }
        }

        private static NpgsqlConnection OpenDbConnection(string connectionString)
        {
            NpgsqlConnection connection;

            while (true)
            {
                try
                {
                    connection = new NpgsqlConnection(connectionString);
                    connection.Open();
                    break;
                }
                catch (SocketException)
                {
                    Console.Error.WriteLine("Waiting for db");
                    Thread.Sleep(1000);
                }
                catch (DbException)
                {
                    Console.Error.WriteLine("Waiting for db");
                    Thread.Sleep(1000);
                }
            }

            Console.Error.WriteLine("Connected to db");

            var command = connection.CreateCommand();
            
            // Create users table
            command.CommandText = @"CREATE TABLE IF NOT EXISTS users (
                                        id SERIAL PRIMARY KEY,
                                        username VARCHAR(255) NOT NULL UNIQUE,
                                        email VARCHAR(255) NOT NULL UNIQUE,
                                        password_hash VARCHAR(255) NOT NULL,
                                        is_admin BOOLEAN DEFAULT FALSE,
                                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                                    )";
            command.ExecuteNonQuery();

            // Create competitions table
            command.CommandText = @"CREATE TABLE IF NOT EXISTS competitions (
                                        id SERIAL PRIMARY KEY,
                                        name VARCHAR(255) NOT NULL,
                                        description TEXT,
                                        option_a VARCHAR(255) NOT NULL,
                                        option_b VARCHAR(255) NOT NULL,
                                        status VARCHAR(50) DEFAULT 'scheduled',
                                        created_by INT REFERENCES users(id),
                                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                        scheduled_start TIMESTAMP,
                                        scheduled_end TIMESTAMP,
                                        started_at TIMESTAMP,
                                        closed_at TIMESTAMP
                                    )";
            command.ExecuteNonQuery();

            // Create votes table with competition reference
            command.CommandText = @"CREATE TABLE IF NOT EXISTS votes (
                                        id VARCHAR(255) NOT NULL,
                                        competition_id INT REFERENCES competitions(id),
                                        user_id INT REFERENCES users(id),
                                        vote VARCHAR(255) NOT NULL,
                                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                        PRIMARY KEY (id, competition_id)
                                    )";
            command.ExecuteNonQuery();

            // Create scheduled tasks table for future automation
            command.CommandText = @"CREATE TABLE IF NOT EXISTS scheduled_tasks (
                                        id SERIAL PRIMARY KEY,
                                        competition_id INT REFERENCES competitions(id) ON DELETE CASCADE,
                                        task_type VARCHAR(50) NOT NULL,
                                        scheduled_time TIMESTAMP NOT NULL,
                                        executed BOOLEAN DEFAULT FALSE,
                                        executed_at TIMESTAMP,
                                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                                    )";
            command.ExecuteNonQuery();

            return connection;
        }

        private static ConnectionMultiplexer OpenRedisConnection(string hostname)
        {
            // Use IP address to workaround https://github.com/StackExchange/StackExchange.Redis/issues/410
            var ipAddress = GetIp(hostname);
            Console.WriteLine($"Found redis at {ipAddress}");

            while (true)
            {
                try
                {
                    Console.Error.WriteLine("Connecting to redis");
                    return ConnectionMultiplexer.Connect(ipAddress);
                }
                catch (RedisConnectionException)
                {
                    Console.Error.WriteLine("Waiting for redis");
                    Thread.Sleep(1000);
                }
            }
        }

        private static string GetIp(string hostname)
            => Dns.GetHostEntryAsync(hostname)
                .Result
                .AddressList
                .First(a => a.AddressFamily == AddressFamily.InterNetwork)
                .ToString();

        private static void UpdateVote(NpgsqlConnection connection, string voterId, string vote, int competitionId, int userId)
        {
            var command = connection.CreateCommand();
            try
            {
                command.CommandText = "INSERT INTO votes (id, competition_id, user_id, vote) VALUES (@id, @competition_id, @user_id, @vote)";
                command.Parameters.AddWithValue("@id", voterId);
                command.Parameters.AddWithValue("@competition_id", competitionId);
                command.Parameters.AddWithValue("@user_id", userId);
                command.Parameters.AddWithValue("@vote", vote);
                command.ExecuteNonQuery();
            }
            catch (DbException)
            {
                command.CommandText = "UPDATE votes SET vote = @vote WHERE id = @id AND competition_id = @competition_id";
                command.Parameters.Clear();
                command.Parameters.AddWithValue("@vote", vote);
                command.Parameters.AddWithValue("@id", voterId);
                command.Parameters.AddWithValue("@competition_id", competitionId);
                command.ExecuteNonQuery();
            }
            finally
            {
                command.Dispose();
            }
        }
    }
}