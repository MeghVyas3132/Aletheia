# 🔐 Security Policy

## Reporting Security Vulnerabilities

If you discover a security vulnerability in MoveH, please report it privately:

- **Email:** [Your Email Here]
- **GitHub:** Use the "Security" tab to report privately

Please do NOT open public issues for security vulnerabilities.

---

## Security Best Practices for Contributors

### 1. **Never Commit Secrets**

❌ **NEVER commit:**
- Private keys (`.aptos/config.yaml`, `APTOS_PRIVATE_KEY`)
- API keys (`GOOGLE_API_KEY`, `TAVILY_API_KEY`, etc.)
- `.env` files
- Any credentials or tokens

✅ **ALWAYS:**
- Use `.env.example` as a template (no real values)
- Keep `.env` files in `.gitignore`
- Use environment variables or secret managers

### 2. **Environment Variables**

**Local Development:**
```bash
cp .env.example .env
# Edit .env with your actual keys
# Never commit .env!
```

**Production/CI/CD:**
- Use GitHub Actions Secrets
- Use AWS Secrets Manager, HashiCorp Vault, or similar
- Never hardcode secrets in workflows

### 3. **Blockchain Private Keys**

**Generate Aptos Keys Securely:**
```bash
# Using Aptos CLI
aptos account create --profile <profile_name>

# Or programmatically (Python)
from aptos_sdk.account import Account
acct = Account.generate()
print("Private key:", acct.to_private_key_hex())
print("Address:", acct.address())
```

**Key Storage:**
- ✅ Store in `.env` (gitignored)
- ✅ Use hardware wallets for production
- ✅ Rotate keys regularly
- ❌ Never share private keys
- ❌ Never commit `.aptos/config.yaml`

### 4. **Code Review Checklist**

Before submitting a PR, verify:
- [ ] No hardcoded API keys or secrets
- [ ] No private keys in code or config files
- [ ] `.env.example` updated (if new variables added)
- [ ] `.gitignore` properly excludes sensitive files
- [ ] No credentials in commit history

### 5. **Git History**

**If you accidentally committed a secret:**

```bash
# DO NOT just delete and recommit - it's still in history!
# You must rewrite history and rotate the compromised key

# Remove from history (use carefully!)
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch path/to/secret/file" \
  --prune-empty --tag-name-filter cat -- --all

# Then rotate the compromised key immediately!
```

**Better approach:** Use tools like `git-secrets` or `gitleaks` to prevent commits with secrets.

### 6. **Frontend Security**

- Never expose backend API keys in frontend code
- Use `NEXT_PUBLIC_*` prefix only for truly public values
- Keep sensitive operations on the backend

### 7. **Dependencies**

```bash
# Regularly check for vulnerabilities
pip audit  # Python
pnpm audit  # Node.js

# Keep dependencies updated
pip install --upgrade -r requirements.txt
pnpm update
```

---

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

---

## Security Features in MoveH

### Blockchain Integrity
- All verdicts are immutably stored on Aptos blockchain
- Cryptographic signatures prevent tampering
- Deduplication prevents duplicate processing

### Data Privacy
- Full reports stored on decentralized Shelby Protocol
- Only metadata and CIDs stored on-chain
- No personal data in smart contracts

### API Security
- Rate limiting (when using Geomi API key)
- Input validation on all endpoints
- Secure key management practices

---

## Questions?

For general security questions, open a GitHub Discussion.
For vulnerabilities, use private reporting channels.

**Remember: Security is everyone's responsibility! 🛡️**
