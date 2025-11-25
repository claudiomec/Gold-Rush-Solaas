# 🔄 Workflow: Editar no Cursor e Enviar para GitHub

## 📝 Processo Simplificado

### Opção 1: Script Automático (Recomendado)

1. **Edite seus arquivos no Cursor** normalmente

2. **Execute o script:**
   ```bash
   ./push_to_github.sh "sua mensagem de commit"
   ```
   
   Ou sem mensagem (usa mensagem automática):
   ```bash
   ./push_to_github.sh
   ```

3. **Pronto!** As alterações serão commitadas e enviadas automaticamente

### Opção 2: Usando VS Code Tasks (No Cursor)

1. **Edite seus arquivos**

2. **Abra o Command Palette** (`Cmd+Shift+P` no Mac)

3. **Digite:** `Tasks: Run Task`

4. **Selecione:** 
   - `Push to GitHub` - Para digitar mensagem personalizada
   - `Push to GitHub (Auto Message)` - Para mensagem automática

5. **Pronto!** As alterações serão enviadas

### Opção 3: Comandos Git Manuais

```bash
# Ver o que mudou
git status

# Adicionar todas as alterações
git add .

# Fazer commit
git commit -m "sua mensagem aqui"

# Enviar para GitHub
git push origin main
```

## 🎯 Fluxo Recomendado

1. ✏️ **Edite** no Cursor
2. 💾 **Salve** os arquivos (`Cmd+S`)
3. 🚀 **Execute** `./push_to_github.sh "descrição das mudanças"`
4. ✅ **Pronto!** Alterações no GitHub

## 📋 Exemplos de Mensagens de Commit

```bash
./push_to_github.sh "feat: Adicionada nova funcionalidade de relatórios"
./push_to_github.sh "fix: Corrigido bug no cálculo de preços"
./push_to_github.sh "style: Melhorado design da interface"
./push_to_github.sh "refactor: Reorganizado código do módulo auth"
```

## ⚡ Atalho Rápido

Crie um alias no seu `.zshrc` ou `.bashrc`:

```bash
alias push-gold="cd ~/Downloads/Gold-Rush-Solaas && ./push_to_github.sh"
```

Depois é só usar:
```bash
push-gold "sua mensagem"
```

## 🔍 Verificar Status

Para ver o que será enviado antes de fazer push:

```bash
git status
git diff
```

---

**💡 Dica:** O script automaticamente detecta todas as alterações e as envia para o GitHub!

