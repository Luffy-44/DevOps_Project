# ⚙️ Ansible Configuration Management — Zestora

> Automated server provisioning, Docker engine installation, and zero-downtime application deployment on AWS EC2.

---

## 📋 Architecture

```
Terraform (Provisions EC2 VM & VPC)
               ↓ (outputs Public IP: 54.234.169.116)
Ansible (Connects over SSH via adm.pem)
   ├── 1. Updates apt packages & security patches
   ├── 2. Installs Docker & Docker Compose v2
   ├── 3. Clones GitHub repository (Luffy-44/DevOps_Project)
   ├── 4. Launches production stack (docker-compose.prod.yml)
   └── 5. Runs health check smoke test on /api/health
```

---

## 🚀 Execution

```bash
# 1. Test SSH connectivity to EC2
ansible -i inventory.ini webservers -m ping

# 2. Run the deployment playbook
ansible-playbook -i inventory.ini deploy-playbook.yml
```

