# Production Deployment Checklist

## ✅ Pre-Deployment Verification

### Code Quality
- [ ] All tests passing
- [ ] No console errors in browser
- [ ] No Docker build warnings
- [ ] No hardcoded secrets or credentials
- [ ] All environment variables documented
- [ ] Code reviewed by team member

### Security Audit
- [ ] HTTPS/SSL certificates ready
- [ ] All default credentials changed
- [ ] CORS headers configured
- [ ] Rate limiting implemented
- [ ] CSRF protection enabled
- [ ] SQL injection prevention verified
- [ ] XSS protection in place
- [ ] Authentication tokens validated
- [ ] Password hashing verified (PBKDF2 with salt)

### Database
- [ ] PostgreSQL version tested (15-alpine)
- [ ] Backup strategy implemented
- [ ] Schema migrations tested
- [ ] Database user has minimal permissions
- [ ] Connection pooling configured
- [ ] Query performance optimized
- [ ] Indexes created on key columns

### Infrastructure
- [ ] Docker images optimized (multi-stage builds)
- [ ] Container registry set up
- [ ] Container scanning enabled
- [ ] Load balancer configured
- [ ] Auto-scaling policies defined
- [ ] Backup and restore tested
- [ ] Disaster recovery plan documented

---

## 🔑 Secrets Management

### Change These Before Deployment
```bash
# In .env file, replace with strong random values:
FLASK_SECRET_KEY=<generate-strong-random-key>
JWT_SECRET=<generate-strong-random-key>

# To generate:
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Secure Secrets Storage
- [ ] Use AWS Secrets Manager (recommended)
- [ ] Use Azure Key Vault
- [ ] Use HashiCorp Vault
- [ ] Use GitHub Secrets (for CI/CD)
- [ ] Never commit .env to git
- [ ] Use .env.example for template only

---

## 🚀 Application Configuration

### Flask Configuration
```python
# vote/app.py must have:
- app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY')
- app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS only
- app.config['SESSION_COOKIE_HTTPONLY'] = True  # No JS access
- app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection
- app.config['PREFERRED_URL_SCHEME'] = 'https'
```

### JWT Token Security
```python
# vote/auth.py must have:
- Token expiry: 24 hours (verify in create_jwt_token)
- Secret key: Changed from dev value
- Algorithm: HS256
- Signature validation: Enabled
```

### Database Security
```python
# vote/app.py must have:
- Connection SSL enabled
- Read-only replica for reports
- User table with proper indexes
- Foreign key constraints enforced
- Triggers for audit logging
```

---

## 🐳 Docker Configuration

### Image Optimization
- [ ] Use specific base image versions (not 'latest')
- [ ] Multi-stage builds implemented
- [ ] Non-root user in Dockerfile
- [ ] Health checks configured
- [ ] Image size < 500MB per service

### Current Dockerfile Issues to Fix
```dockerfile
# vote/Dockerfile - Production Stage
FROM python:3.11-slim as production
WORKDIR /usr/local/app

# Add non-root user
RUN useradd -m -u 1000 appuser

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY vote/ .

# Change ownership
RUN chown -R appuser:appuser .
USER appuser

# Health check
HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost/health')"

# Use gunicorn instead of flask dev server
CMD ["gunicorn", "--bind", "0.0.0.0:80", "--workers", "4", "--worker-class", "sync", "app:app"]
```

### Requirements Update
```
gunicorn>=21.0.0
```

---

## 🔒 HTTPS/SSL Configuration

### SSL Certificate Setup
```bash
# Option 1: Let's Encrypt (Recommended)
certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Option 2: Self-signed (Development)
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365
```

### Nginx Reverse Proxy (Recommended)
```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    # SSL best practices
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    location / {
        proxy_pass http://vote:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

---

## 📊 Monitoring & Logging

### Application Logging
- [ ] All requests logged with timestamp
- [ ] Error stack traces logged
- [ ] Database queries logged (non-production)
- [ ] Authentication events logged
- [ ] Vote processing logged
- [ ] Logs shipped to centralized storage

### Metrics Collection
- [ ] Prometheus metrics exposed on /metrics
- [ ] CPU and memory usage monitored
- [ ] Database connection pool monitored
- [ ] Redis memory monitored
- [ ] Request latency tracked
- [ ] Error rates monitored

### Alerting
- [ ] Service down alert
- [ ] High error rate alert (>5%)
- [ ] Database connection limit alert
- [ ] Disk space alert
- [ ] Memory leak detection

### Grafana Dashboards
- [ ] Application health dashboard
- [ ] Vote counting in real-time
- [ ] Database performance metrics
- [ ] Infrastructure metrics

---

## 🧪 Load Testing

### Before Production Deployment
```bash
# Test 1000 concurrent users, 10,000 votes
ab -n 10000 -c 1000 http://localhost:8080/health

# Test vote endpoint with high load
siege -u http://localhost:8080/vote/1 -c 100 -r 100

# Monitor during test
docker stats
```

### Expected Results
- Vote processing latency < 500ms
- 99th percentile latency < 2000ms
- Zero data loss
- No connection pool exhaustion
- Database remains responsive

---

## 🔄 CI/CD Pipeline

### GitHub Actions Workflow
```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Build Docker images
        run: docker compose build
      
      - name: Run tests
        run: docker compose run --rm vote pytest
      
      - name: Security scan
        run: docker scan --severity high vote
      
      - name: Push to registry
        run: |
          docker tag vote:latest myregistry.azurecr.io/vote:latest
          docker push myregistry.azurecr.io/vote:latest
      
      - name: Deploy to production
        run: |
          kubectl set image deployment/vote-app \
            vote=myregistry.azurecr.io/vote:latest
```

---

## 📈 Performance Optimization

### Current Bottlenecks to Address
1. **Real-time updates**: Polling every 3 seconds → Consider WebSocket
2. **Database**: Single instance → Add read replicas
3. **Vote processing**: Single worker → Scale worker pods
4. **Caching**: No caching on competitions list → Add Redis cache

### Optimization Tasks
- [ ] Add Redis caching for competitions list
- [ ] Implement database query caching
- [ ] Add CDN for static assets
- [ ] Implement WebSocket for real-time updates
- [ ] Add database indexes on frequently queried columns
- [ ] Use connection pooling for database
- [ ] Enable gzip compression
- [ ] Minimize CSS/JS files

### Database Optimization
```sql
-- Add indexes for frequently queried columns
CREATE INDEX idx_votes_competition_id ON votes(competition_id);
CREATE INDEX idx_votes_user_id ON votes(user_id);
CREATE INDEX idx_votes_created_at ON votes(created_at);
CREATE INDEX idx_competitions_status ON competitions(status);

-- Verify indexes are used
EXPLAIN ANALYZE SELECT * FROM votes WHERE competition_id = 1;
```

---

## 🛠️ Kubernetes Deployment

### Deployment Manifest
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vote-app
  labels:
    app: vote
spec:
  replicas: 3
  selector:
    matchLabels:
      app: vote
  template:
    metadata:
      labels:
        app: vote
    spec:
      containers:
      - name: vote
        image: myregistry.azurecr.io/vote:latest
        ports:
        - containerPort: 80
        env:
        - name: FLASK_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: vote-secrets
              key: flask-secret
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 80
          initialDelaySeconds: 10
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 80
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: vote-service
spec:
  selector:
    app: vote
  ports:
  - port: 80
    targetPort: 80
  type: LoadBalancer
```

---

## 🔐 Security Hardening Checklist

### Application Level
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention (use parameterized queries)
- [ ] XSS prevention (escape all user input)
- [ ] CSRF tokens on all forms
- [ ] Rate limiting on login/register endpoints
- [ ] Account lockout after 5 failed login attempts
- [ ] Password requirements enforced
- [ ] Session timeout after 30 minutes inactivity

### Infrastructure Level
- [ ] Firewall rules configured
- [ ] VPN required for admin access
- [ ] SSH key-based authentication only
- [ ] Automatic security updates enabled
- [ ] Container vulnerability scanning enabled
- [ ] Network policies restrict inter-container traffic
- [ ] Secrets rotated every 90 days

### Data Protection
- [ ] Database encryption at rest
- [ ] Data encryption in transit (HTTPS/TLS)
- [ ] Backup encryption enabled
- [ ] Data retention policies defined
- [ ] PII compliance verified
- [ ] GDPR compliance reviewed

---

## 📋 Post-Deployment Verification

### Functional Testing
```bash
# Test registration flow
curl -X POST http://yoursite.com/register \
  -F "username=test" \
  -F "email=test@example.com" \
  -F "password=Pass123!" \
  -F "confirm_password=Pass123!"

# Test login
curl -X POST http://yoursite.com/login \
  -F "username=test" \
  -F "password=Pass123!"

# Test voting
curl -X POST http://yoursite.com/vote/1 \
  -F "vote=a" \
  -H "Authorization: Bearer $TOKEN"

# Test admin creation
curl -X POST http://yoursite.com/api/admin/competitions \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"New Competition","option_a":"A","option_b":"B"}'
```

### Performance Testing
- [ ] Page load time < 2 seconds
- [ ] Vote submission < 500ms
- [ ] Admin dashboard responsive
- [ ] No memory leaks over 24 hours
- [ ] Database response time < 100ms

### Monitoring Verification
- [ ] Metrics being collected
- [ ] Alerts configured and testing
- [ ] Logs aggregating properly
- [ ] Dashboard showing real-time data
- [ ] Backup jobs running

---

## 🚨 Incident Response

### If Service Goes Down
1. Check service status: `kubectl get pods`
2. Check logs: `kubectl logs pod-name`
3. Check database connectivity
4. Check Redis connectivity
5. Restart service: `kubectl rollout restart deployment/vote-app`
6. If still down, roll back: `kubectl rollout undo deployment/vote-app`
7. Notify team
8. Document incident

### If Database Corrupted
1. Restore from last backup
2. Replay vote transactions
3. Verify data integrity
4. Check for data loss
5. Post-incident review

### If Performance Degradation
1. Check CPU/memory usage
2. Check database slow query log
3. Check connection pool exhaustion
4. Scale up if needed
5. Optimize slow queries

---

## 📞 Deployment Contacts

- **DevOps Lead**: [Name]
- **Database Admin**: [Name]
- **Security Officer**: [Name]
- **Application Owner**: [Name]

---

## ✅ Final Checklist Before Go-Live

- [ ] All environment variables set
- [ ] Secrets rotated and secured
- [ ] SSL certificates installed
- [ ] Database backups tested
- [ ] Monitoring and alerting active
- [ ] Load balancer configured
- [ ] DNS records updated
- [ ] Documentation updated
- [ ] Team trained
- [ ] Runbook created
- [ ] Incident response plan ready
- [ ] Communication plan established

**Date Approved**: _____________
**Approved By**: _____________
**Deployment Date**: _____________

