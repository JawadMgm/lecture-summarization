const mongoose = require('mongoose');

const lectureSchema = new mongoose.Schema({
    user: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true },
    title: { type: String, required: true },
    videoPath: { type: String, default: '' },
    sourceUrl: { type: String, default: '' },
    transcript: { type: String, default: '' },
    summary: { type: String, default: '' },
    easyExplanation: { type: String, default: '' },
    topicBreakdown: [{
        title: { type: String },
        content: { type: String },
    }],
    importantNotes: [{ type: String }],
    keyTerms: [{
        term: { type: String },
        definition: { type: String },
    }],
    formulas: [{ type: String }],
    practiceProblems: [{ type: String }],
    keywords: [{ type: String }],
    status: { type: String, enum: ['Processing', 'Completed', 'Failed'], default: 'Processing' },
    processingStage: { type: String, default: '' },
    errorMessage: { type: String, default: '' },
    createdAt: { type: Date, default: Date.now },
});

module.exports = mongoose.model('Lecture', lectureSchema);
