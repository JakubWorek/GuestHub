// Server dependencies
const express = require('express');
const cors = require('cors');
const cookieParser = require('cookie-parser');
// AWS S3 dependencies
const {S3Client, PutObjectCommand} = require('@aws-sdk/client-s3');
const imageDownloader = require('image-downloader');
const fs = require('fs');
const multer = require('multer');
const mime = require('mime-types');

// Configurations
require('dotenv').config();
const app = express();

const bucket = 'wdai-course-project';

app.use(express.json());
app.use(cookieParser());
app.use('/uploads', express.static(__dirname+'/uploads'));
app.use(cors({
  credentials: true,
  origin: 'http://localhost:5173',
}));

// AWS S3 functions
async function uploadToS3(path, originalFilename, mimetype) {
  const client = new S3Client({
    region: 'eu-north-1',
    credentials: {
      accessKeyId: process.env.S3_ACCESS_KEY,
      secretAccessKey: process.env.S3_SECRET_ACCESS_KEY,
    },
  });
  const parts = originalFilename.split('.');
  const ext = parts[parts.length - 1];
  const newFilename = Date.now() + '.' + ext;
  await client.send(new PutObjectCommand({
    Bucket: bucket,
    Body: fs.readFileSync(path),
    Key: newFilename,
    ContentType: mimetype,
    ACL: 'public-read',
  }));
  return `https://${bucket}.s3.amazonaws.com/${newFilename}`;
}

// Routes
app.get('/api/test', (req,res) => {
  res.json('test ok');
});

app.post('/api/upload-by-link', async (req,res) => {
  const {link} = req.body;
  const newName = 'photo' + Date.now() + '.jpg';
  await imageDownloader.image({
    url: link,
    dest: '/tmp/' +newName,
  });
  const url = await uploadToS3('/tmp/' +newName, newName, mime.lookup('/tmp/' +newName));
  res.json(url);
});

const photosMiddleware = multer({dest:'/tmp'});
app.post('/api/upload', photosMiddleware.array('photos', 100), async (req,res) => {
  const uploadedFiles = [];
  for (let i = 0; i < req.files.length; i++) {
    const {path,originalname,mimetype} = req.files[i];
    const url = await uploadToS3(path, originalname, mimetype);
    uploadedFiles.push(url);
  }
  res.json(uploadedFiles);
});

app.listen(4000);