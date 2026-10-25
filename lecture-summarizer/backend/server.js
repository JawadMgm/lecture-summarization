require('dotenv').config();
const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');
const connectDB = require('./config/db');
const lectureRoutes = require('./routes/lectureRoutes');

const uploadsDir = path.join(__dirname, 'uploads');
if (!fs.existsSync(uploadsDir)) {
    fs.mkdirSync(uploadsDir, { recursive: true });
}

const app = express();
connectDB();

app.use(cors());
app.use(express.json());

app.get('/', (_req, res) => {
    res.json({
        name: 'Lecture Summarizer API',
        status: 'running',
        frontend: 'http://localhost:3000',
        endpoints: {
            health: 'GET /health',
            listLectures: 'GET /api/lectures',
            uploadVideo: 'POST /api/lectures/upload',
            fromUrl: 'POST /api/lectures/from-url',
            getLecture: 'GET /api/lectures/:id',
        },
    });
});

app.get('/health', (_req, res) => {
    res.json({ status: 'ok' });
});

app.use('/api/lectures', lectureRoutes);
app.use('/api/auth', require('./routes/authRoutes'));

const PORT = process.env.PORT || 5001;
app.listen(PORT, () => console.log(`Backend running on port ${PORT}`));
