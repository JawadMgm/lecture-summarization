const Lecture = require('../models/Lecture');
const axios = require('axios');
const path = require('path');

const AI_SERVICE_URL = process.env.AI_SERVICE_URL || 'http://localhost:8000';

async function runAiProcessing(lecture, endpoint, payload, stage) {
    try {
        lecture.processingStage = stage;
        await lecture.save();
        
        console.log(`Hitting AI Service at: ${AI_SERVICE_URL}${endpoint}`);

        const aiResponse = await axios.post(`${AI_SERVICE_URL}${endpoint}`, payload, { timeout: 0 });

        lecture.transcript = aiResponse.data.transcript;
        lecture.summary = aiResponse.data.summary;
        lecture.easyExplanation = aiResponse.data.easyExplanation || '';
        lecture.topicBreakdown = aiResponse.data.topicBreakdown || [];
        lecture.importantNotes = (aiResponse.data.importantNotes || []).map(i => typeof i === 'string' ? i : JSON.stringify(i));
        lecture.keyTerms = aiResponse.data.keyTerms || [];
        
        // Defensively sanitize formulas and keywords to string arrays
        lecture.formulas = (aiResponse.data.formulas || []).map(f => typeof f === 'string' ? f : (f.formula || JSON.stringify(f)));
        lecture.practiceProblems = (aiResponse.data.practiceProblems || []).map(p => typeof p === 'string' ? p : JSON.stringify(p));
        lecture.keywords = (aiResponse.data.keywords || []).map(k => typeof k === 'string' ? k : (k.keyword || JSON.stringify(k)));

        lecture.status = 'Completed';
        lecture.processingStage = '';
        
        try {
            await lecture.save();
        } catch (saveError) {
            console.error("Mongoose save error:", saveError);
            lecture.status = 'Failed';
            lecture.errorMessage = 'Failed to save generated notes to database.';
            await lecture.save().catch(e => console.error("Fatal db error", e));
        }
    } catch (aiError) {
        const detail = aiError.response?.data?.detail || aiError.message;
        console.error('AI Error:', detail);
        lecture.status = 'Failed';
        lecture.processingStage = '';
        lecture.errorMessage = typeof detail === 'string' ? detail : JSON.stringify(detail);
        await lecture.save();
    }
}

exports.uploadAndProcessLecture = async (req, res) => {
    try {
        if (!req.file) return res.status(400).json({ message: 'No video uploaded' });

        const newLecture = new Lecture({
            user: req.user.id,
            title: req.body.title || 'Untitled Lecture',
            videoPath: path.resolve(req.file.path),
        });
        await newLecture.save();

        res.status(202).json({
            message: 'Upload successful. Processing started.',
            lectureId: newLecture._id,
        });

        runAiProcessing(newLecture, '/process-video', {
            lectureId: newLecture._id,
            videoPath: newLecture.videoPath,
        }, 'Transcribing audio and generating notes…');
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
};

exports.processFromUrl = async (req, res) => {
    try {
        const { title, url } = req.body;

        if (!url) return res.status(400).json({ message: 'Video URL is required' });

        try {
            new URL(url);
        } catch {
            return res.status(400).json({ message: 'Invalid URL format' });
        }

        const newLecture = new Lecture({
            user: req.user.id,
            title: title || 'Untitled Lecture',
            sourceUrl: url,
        });
        await newLecture.save();

        res.status(202).json({
            message: 'URL received. Downloading and processing started.',
            lectureId: newLecture._id,
        });

        const isYoutube = /youtube\.com|youtu\.be/.test(url);
        runAiProcessing(newLecture, '/process-url', {
            lectureId: newLecture._id,
            url,
        }, isYoutube ? 'Fetching captions and writing notes…' : 'Downloading audio and generating notes…');
    } catch (error) {
        console.error("Error in processFromUrl:", error);
        res.status(500).json({ error: error.message });
    }
};

exports.getLectureDetails = async (req, res) => {
    try {
        const lecture = await Lecture.findById(req.params.id);
        if (!lecture) return res.status(404).json({ message: 'Lecture not found' });
        
        if (lecture.user.toString() !== req.user.id) {
            return res.status(403).json({ message: 'Not authorized to view this lecture' });
        }

        res.status(200).json(lecture);
    } catch (error) {
        res.status(404).json({ message: 'Lecture not found' });
    }
};

exports.listLectures = async (req, res) => {
    try {
        const lectures = await Lecture.find({ user: req.user.id })
            .select('title status createdAt summary sourceUrl importantNotes')
            .sort({ createdAt: -1 });
        res.status(200).json(lectures);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
};
