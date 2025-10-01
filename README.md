# Система управления заявлениями на практику

Это веб-приложение на Flask для управления заявками студентов на практику. Система позволяет студентам заполнять заявки на практику, а преподавателям - просматривать и управлять этими заявками.

## Функциональность

### Для студентов:
- Регистрация и авторизация
- Заполнение заявок на практику
- Просмотр статуса заявок
- Повторное заполнение отклоненных заявок
- Скачивание PDF-документа с заявкой

### Для преподавателей:
- Просмотр списка групп и студентов
- Просмотр заявок студентов
- Одобрение или отклонение заявок

## Установка и запуск

### Требования
- Python 3.8+
- PostgreSQL

### Шаги установки

1. Клонировать репозиторий:
```
git clone <url-репозитория>
cd gpo_my
```

2. Создать и активировать виртуальное окружение:
```
python -m venv venv
# Для Windows
venv\Scripts\activate
# Для Linux/Mac
source venv/bin/activate
```

3. Установить зависимости:
```
pip install -r requirements.txt
```

4. Создать базу данных PostgreSQL:
```
createdb gpo_practice
```

5. Настроить переменные окружения (создать файл .env):
```
SECRET_KEY=your_secret_key
DATABASE_URL=postgresql://username:password@localhost/gpo_practice
```

6. Инициализировать базу данных:
```
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

7. Запустить приложение:
```
python app.py
```

## Структура проекта

- `app.py` - Основной файл приложения
- `models.py` - Модели данных
- `routes/` - Маршруты приложения
  - `auth.py` - Маршруты аутентификации
  - `main.py` - Основные маршруты
- `templates/` - HTML-шаблоны
- `ShABLON_732_grupp_Zayavlenie_na_prokhozhdenie_praktiki-1.pdf` - Шаблон PDF для заявки

## Технологии

- Flask - веб-фреймворк
- SQLAlchemy - ORM для работы с базой данных
- PostgreSQL - СУБД
- Flask-Login - аутентификация пользователей
- ReportLab и PyPDF - работа с PDF-документами
- Bootstrap - фронтенд-фреймворк 

# Flask DDoS Protection System

A comprehensive DDoS protection system for Flask web applications implementing multiple defense mechanisms against various types of DDoS attacks. This implementation is fully compatible with Windows 10.

## Protection Features

1. **SYN Flood Protection**
   - Recommendations for Windows Defender Firewall configuration
   - Windows registry settings for TCP/IP hardening
   - IIS-specific configuration options

2. **HTTP Flood Protection**
   - Rate limiting per IP address with configurable thresholds
   - Distributed tracking using Redis
   - Fallback to in-memory tracking when Redis is unavailable

3. **Slowloris Protection**
   - Connection limiting per IP address
   - Configurable connection timeouts
   - Automatic connection tracking and cleanup

4. **Caching Implementation**
   - Server-side caching to reduce resource utilization
   - Support for Redis and Windows-compatible filesystem caching

5. **Anomaly Detection**
   - Real-time traffic monitoring
   - Automatic detection of suspicious behavior
   - Configurable thresholds and response mechanisms

6. **Additional Features**
   - IP blacklisting for repeat offenders
   - Whitelisting for trusted IPs
   - Geographic traffic filtering
   - Request validation to identify suspicious patterns
   - Integration with load balancers and CDN services

## Installation on Windows 10

1. Install required dependencies:
   ```
   pip install -r requirements.txt
   ```

2. For geo-filtering, download and place the MaxMind GeoLite2 Country database in your project directory:
   ```
   # Visit https://dev.maxmind.com/geoip/geolite2-free-geolocation-data to get the database
   # Download the GeoLite2 Country database and extract the .mmdb file to your project directory
   ```

3. Install Redis for Windows (optional but recommended):
   
   **Option 1: Windows Subsystem for Linux (WSL)**
   ```
   # Install WSL if not already installed
   wsl --install
   
   # Once WSL is installed, open a WSL terminal and run:
   sudo apt-get update
   sudo apt-get install redis-server
   
   # Start Redis
   sudo service redis-server start
   ```
   
   **Option 2: Redis Windows Port by Microsoft**
   ```
   # Download the Redis Windows port from:
   # https://github.com/microsoftarchive/redis/releases
   
   # Run the MSI installer and follow the installation wizard
   # Redis will be installed as a Windows Service and will start automatically
   ```
   
   **Option 3: Docker Desktop for Windows**
   ```
   # Install Docker Desktop for Windows
   # Then run Redis in a container:
   docker run --name redis -p 6379:6379 -d redis
   ```

4. Configure Windows to better handle SYN flood attacks (requires admin privileges):
   
   Open PowerShell as Administrator and run:
   ```powershell
   # Enable SYN flood protection
   Set-NetTCPSetting -SettingName InternetCustom -SynAttackProtect 2
   
   # Reduce retransmission timeouts
   Set-NetTCPSetting -SettingName InternetCustom -InitialRto 1000
   
   # Reduce TCP max connect retransmissions
   Set-NetTCPSetting -SettingName InternetCustom -TcpMaxConnectRetransmissions 2
   ```

## Usage

### Basic Integration

```python
from flask import Flask
from ddos_protection import protect_flask_app

app = Flask(__name__)

# Apply all DDoS protection features with default settings
cache = protect_flask_app(app)

@app.route('/')
def index():
    return "Protected homepage"

if __name__ == '__main__':
    app.run()
```

### Advanced Integration with Custom Settings

```python
from flask import Flask
from ddos_protection import protect_flask_app, rate_limit, geo_filter

app = Flask(__name__)

# Custom DDoS protection configuration
ddos_config = {
    "RATE_LIMIT": 100,                    # Max requests per minute per IP
    "RATE_LIMIT_WINDOW": 60,              # Window size in seconds
    "MAX_CONNECTIONS_PER_IP": 20,         # Max concurrent connections per IP
    "CONNECTION_TIMEOUT": 30,             # Connection timeout in seconds
    "BLACKLIST_THRESHOLD": 5,             # Violations before blacklisting
    "BLACKLIST_DURATION": 3600,           # Blacklist duration in seconds
    "WHITELISTED_IPS": set(['127.0.0.1', '::1']), # Whitelisted IPs including IPv6 localhost
    "GEO_BLOCKING_ENABLED": True,         # Enable geo-blocking
    "BLOCKED_COUNTRIES": ['XY', 'ZZ'],    # Countries to block
    "ANOMALY_DETECTION_ENABLED": True,    # Enable anomaly detection
}

# Apply protection with custom settings
cache = protect_flask_app(app, ddos_config)

# Apply rate limiting to specific routes
@app.route('/api/data')
@rate_limit()
def api_data():
    return {"status": "success"}

# Apply geo-filtering to sensitive routes
@app.route('/admin')
@rate_limit()
@geo_filter()
def admin():
    return "Admin area"

if __name__ == '__main__':
    app.run()
```

### Windows Production Deployment

For production environments on Windows, there are several options:

**IIS with FastCGI and WSGI** (Recommended for Windows servers):
1. Install IIS and the CGI role feature:
   ```
   dism /Online /Enable-Feature /FeatureName:IIS-CGI
   ```
2. Install the WSGI handler:
   ```
   pip install wfastcgi
   wfastcgi-enable
   ```
3. Configure IIS with web.config file:
   ```xml
   <configuration>
     <system.webServer>
       <handlers>
         <add name="Python FastCGI" 
              path="*" 
              verb="*" 
              modules="FastCgiModule" 
              scriptProcessor="C:\path\to\python.exe|C:\path\to\wfastcgi.py" 
              resourceType="Unspecified" 
              requireAccess="Script" />
       </handlers>
       <security>
         <requestFiltering>
           <!-- Set connection limits for Slowloris protection -->
           <requestLimits maxAllowedContentLength="30000000" maxQueryString="2048" maxUrl="4096">
             <headerLimits>
               <!-- Limit header size to protect against large header attacks -->
               <add header="Content-type" sizeLimit="100" />
             </headerLimits>
           </requestLimits>
         </requestFiltering>
       </security>
     </system.webServer>
     <appSettings>
       <add key="WSGI_HANDLER" value="app.app" />
       <add key="PYTHONPATH" value="C:\path\to\your\app" />
     </appSettings>
   </configuration>
   ```

**Waitress WSGI Server** (Easy to set up on Windows):
```
pip install waitress
waitress-serve --port=8000 --call app:app
```

**Gunicorn with WSL** (If you're using WSL):
```
# In WSL terminal
cd /mnt/c/path/to/your/app
gunicorn -w 4 -b 0.0.0.0:5000 --backlog 1024 app:app
```

### Windows Firewall Configuration

Configure Windows Defender Firewall to better protect against DDoS:

1. Open Windows Defender Firewall with Advanced Security:
   ```
   wf.msc
   ```

2. Create a new inbound rule to limit connections:
   - Select "Custom Rule" > "All Programs"
   - For protocol, choose TCP
   - Specify your application port (e.g., 5000)
   - Set action to "Allow"
   - Apply to Domain, Private, and Public profiles
   - Name it "Flask Application"

3. Configure rate limiting using third-party firewall software like Comodo Firewall or Windows Server-specific features.

## Integration with CDN/DDoS Protection Services

For enterprise-level protection on Windows environments, consider integrating with:

1. **Cloudflare** - Provides DDoS protection and CDN services
2. **Microsoft Azure Front Door** - DDoS protection for web applications
3. **Imperva** - Enterprise-grade DDoS protection
4. **Akamai** - Global CDN with DDoS mitigation

## Windows-Specific Troubleshooting

1. **Redis Connection Issues**:
   - Ensure Redis service is running: `sc query redis`
   - Check firewall settings: `netsh advfirewall firewall show rule name=Redis`
   - Add firewall rule if needed: 
     ```
     netsh advfirewall firewall add rule name="Redis" dir=in action=allow protocol=TCP localport=6379
     ```

2. **GeoIP Database Issues**:
   - Ensure the path uses correct Windows path format
   - Default path is set to current working directory: `os.path.join(os.getcwd(), "GeoLite2-Country.mmdb")`
   - If problems persist, provide absolute path in your config

3. **File Permission Issues**:
   - Run your Flask application with sufficient permissions
   - For cache files, ensure the application has write access to the directory

## License

MIT 