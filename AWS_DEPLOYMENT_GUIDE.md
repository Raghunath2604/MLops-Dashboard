# AWS EC2 Deployment Guide - ML Dashboard

## 🚀 Step-by-Step Deployment

### STEP 1: Launch EC2 Instance

1. **Login to AWS Console**
   - Go to https://aws.amazon.com
   - Sign in with your credentials

2. **Launch EC2 Instance**
   - Go to EC2 → Instances → Launch Instance
   - **AMI**: Ubuntu 24.04 LTS (free tier eligible)
   - **Instance Type**: t3.small (recommended) or t2.micro (free tier)
   - **Storage**: 30 GB (free tier: 30 GB included)
   - **Security Group**: Allow ports 22 (SSH), 80 (HTTP), 443 (HTTPS), 8001 (API), 3001 (Grafana)
   - **Key Pair**: Create & download (save safely!)

3. **Wait for Instance to Start**
   - Status should show "Running"
   - Note the **Public IPv4 address** (e.g., `3.123.45.67`)

---

### STEP 2: Connect to Instance

```bash
# On your local machine (where you downloaded the key)

# Make key readable (Mac/Linux)
chmod 400 your-key.pem

# SSH into instance
ssh -i your-key.pem ubuntu@3.123.45.67
# (replace with your actual IP)
```

---

### STEP 3: Install Docker

```bash
# SSH into instance, then run:

# Update packages
sudo apt update && sudo apt upgrade -y

# Install Docker
sudo apt install -y docker.io docker-compose

# Add user to docker group (avoid sudo)
sudo usermod -aG docker ubuntu
newgrp docker

# Verify
docker --version
docker-compose --version
```

---

### STEP 4: Clone & Deploy Project

```bash
# Clone your project (or upload files)
git clone https://github.com/your-username/mldashborad.git
cd mldashborad

# OR if using file upload:
# Upload files via SCP or other method
# scp -r -i your-key.pem ./mldashborad ubuntu@3.123.45.67:/home/ubuntu/

# Create .env file with your secrets
cat > .env << 'EOF'
DATABASE_URL=postgresql+asyncpg://mluser:mlpassword@postgres:5432/mldb
SECRET_KEY=your-secure-key-here-change-this
LOG_LEVEL=INFO
EOF

# Start services
docker-compose up -d

# Wait 30 seconds
sleep 30

# Check status
docker-compose ps
```

---

### STEP 5: Access Your Application

```
API:       http://3.123.45.67:8001/health
Grafana:   http://3.123.45.67:3001 (admin/admin)
Prometheus: http://3.123.45.67:9091
```

---

### STEP 6: Setup Domain (Optional but Recommended)

```bash
# Option A: Use AWS Route53 (paid)
# Option B: Use free domain with DuckDNS
# Option C: Access via IP address

# For HTTPS, add Nginx reverse proxy with Let's Encrypt:
sudo apt install nginx certbot python3-certbot-nginx -y
# (See additional nginx setup below)
```

---

### STEP 7: Enable Auto-Start on Reboot

```bash
# Create systemd service to auto-start Docker on reboot
sudo tee /etc/systemd/system/ml-dashboard.service > /dev/null << 'EOF'
[Unit]
Description=ML Dashboard Docker Services
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
User=ubuntu
WorkingDirectory=/home/ubuntu/mldashborad
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

# Enable it
sudo systemctl enable ml-dashboard.service
sudo systemctl start ml-dashboard.service
```

---

### STEP 8: Setup Monitoring & Backups

```bash
# SSH into instance

# Setup automated PostgreSQL backups
mkdir -p /home/ubuntu/backups

# Create backup script
cat > /home/ubuntu/backup-db.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/ubuntu/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
docker-compose exec -T postgres pg_dump -U mluser mldb > \
  $BACKUP_DIR/backup_$TIMESTAMP.sql
echo "Backup created: backup_$TIMESTAMP.sql"
EOF

chmod +x /home/ubuntu/backup-db.sh

# Add to crontab (daily backups at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /home/ubuntu/backup-db.sh") | crontab -
```

---

### STEP 9: Monitor Logs

```bash
# SSH into instance

# View real-time logs
docker-compose logs -f fastapi

# View specific service
docker-compose logs -f postgres

# View all logs
docker-compose logs -f
```

---

### STEP 10: Update & Maintain

```bash
# SSH into instance

# Pull latest code
cd /home/ubuntu/mldashborad
git pull origin main

# Rebuild & restart
docker-compose build --no-cache
docker-compose up -d

# Check status
docker-compose ps
```

---

## 💰 AWS Cost Estimate

| Component | Monthly Cost | Notes |
|-----------|--------------|-------|
| EC2 t3.small | ~$10 | 730 hours/month |
| Data Transfer | ~$1 | Minimal outbound |
| Storage (EBS) | ~$3 | 30 GB gp3 |
| **Total** | **~$14/month** | Very affordable |

**Free Tier eligible:** EC2 t2.micro (1 GB RAM) - may be tight for BERT model

---

## 🔒 Security Best Practices

### 1. Secure Your .env File
```bash
# Never commit .env to git
echo ".env" >> .gitignore
git add .gitignore
git commit -m "Add .env to gitignore"
```

### 2. Use AWS Secrets Manager (Optional)
```bash
# Instead of .env, store secrets in AWS
aws secretsmanager create-secret --name ml-dashboard-secrets \
  --secret-string '{"SECRET_KEY":"your-key","DB_PASSWORD":"your-password"}'
```

### 3. Enable Security Group Rules
```
Inbound:
- Port 22 (SSH): Only from YOUR IP
- Port 80 (HTTP): 0.0.0.0/0
- Port 443 (HTTPS): 0.0.0.0/0
- Port 8001 (API): 0.0.0.0/0 (or restrict to your IP)
- Port 3001 (Grafana): 0.0.0.0/0 (consider restricting)

Outbound:
- All traffic (needed for Docker pulls, updates)
```

### 4. Set Database Password
```bash
# In docker-compose.yml, change default password:
environment:
  POSTGRES_PASSWORD: your-secure-password-here
  POSTGRES_USER: mluser
```

### 5. Backup Strategy
```bash
# Daily backups (see Step 8)
# Weekly backups to S3
# Monthly full snapshots

# Download backup locally
scp -i your-key.pem ubuntu@3.123.45.67:/home/ubuntu/backups/backup_*.sql ./
```

---

## 🆘 Troubleshooting

### Problem: Can't connect to instance
```bash
# Check security group allows SSH port 22
# Check key permissions: chmod 400 your-key.pem
# Check IP is correct: aws ec2 describe-instances
```

### Problem: Docker not starting
```bash
# SSH into instance
docker ps
# If error: sudo service docker start
```

### Problem: Out of disk space
```bash
# Check usage
df -h

# Clean up Docker
docker system prune -a
```

### Problem: PostgreSQL won't start
```bash
# Check logs
docker-compose logs postgres

# May need to delete corrupted volume
docker-compose down -v
docker-compose up -d postgres
```

### Problem: High memory usage
```bash
# Check usage
docker stats

# Limit BERT model loading in app.py
# Use smaller model: distilbert-base-uncased (already using)
```

---

## ✅ Deployment Checklist

- [ ] AWS account created
- [ ] EC2 instance launched (t3.small or t2.micro)
- [ ] Security group configured (ports 22, 80, 443, 8001, 3001)
- [ ] SSH key downloaded and secured
- [ ] Connected via SSH successfully
- [ ] Docker installed and working
- [ ] Project cloned or uploaded
- [ ] .env file created with SECRET_KEY
- [ ] docker-compose up -d completed
- [ ] All 6 services running (docker-compose ps)
- [ ] API responding (/health endpoint)
- [ ] Grafana accessible (port 3001)
- [ ] PostgreSQL backups configured
- [ ] Monitoring logs reviewed
- [ ] Security group rules verified

---

## 📞 After Deployment

### Test Everything Works
```bash
curl http://3.123.45.67:8001/health
curl http://3.123.45.67:8001/predict?text=Test
```

### Create Grafana Dashboards
```
Open: http://3.123.45.67:3001
Login: admin/admin
Create dashboards using PostgreSQL data
```

### Monitor Daily
```bash
# SSH and check status
docker-compose ps

# View logs for errors
docker-compose logs -f fastapi | grep ERROR

# Check disk usage
df -h
```

---

## 🎯 Next Steps

1. **Deploy to AWS** (follow steps above)
2. **Configure domain** (optional but recommended)
3. **Setup SSL/HTTPS** (for production)
4. **Create Grafana dashboards**
5. **Configure alerts** in Grafana
6. **Setup monitoring** (CloudWatch optional)
7. **Plan backup strategy**
8. **Document your setup**

---

## 📚 Useful AWS Commands

```bash
# List instances
aws ec2 describe-instances --region us-east-1

# Stop instance (to save money)
aws ec2 stop-instances --instance-ids i-1234567890abcdef0

# Start instance
aws ec2 start-instances --instance-ids i-1234567890abcdef0

# Get instance IP
aws ec2 describe-instances --query 'Reservations[0].Instances[0].PublicIpAddress'
```

---

**Good luck with deployment! 🚀**
