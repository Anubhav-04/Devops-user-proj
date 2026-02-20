require("dotenv").config();
const express = require("express");
const mongoose = require("mongoose");
const cors = require("cors");
const multer = require("multer");
const csv = require("csv-parser");
const fs = require("fs");
const path = require("path");

const User = require("./models/User");

const app = express();

app.use(cors());
app.use(express.json());
app.use(express.static("public"));
app.use("/uploads", express.static("uploads"));

/* ---------- MongoDB ---------- */

mongoose.connect(process.env.MONGO_URI)
.then(() => console.log("MongoDB Connected"))
.catch(err => console.log(err));

/* ---------- Multer Config ---------- */

const storage = multer.diskStorage({
  destination: "uploads/",
  filename: (req, file, cb) => {
    cb(null, Date.now() + "-" + file.originalname);
  }
});

const upload = multer({ storage });
const csvUpload = multer({ dest: "uploads/" });

/* ---------- APIs ---------- */

// ✅ Create user with image
app.post("/api/users", upload.single("image"), async (req, res) => {
  try {
    const user = new User({
      name: req.body.name,
      email: req.body.email,
      age: req.body.age,
      city: req.body.city,
      image: req.file ? `/uploads/${req.file.filename}` : null
    });

    await user.save();
    res.json({ message: "User saved", user });

  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ✅ Get all users
app.get("/api/users", async (req, res) => {
  const users = await User.find();
  res.json(users);
});

// ✅ Search by name or email
app.get("/api/users/search", async (req, res) => {
  const { name, email } = req.query;

  const users = await User.find({
    $or: [
      name ? { name: new RegExp(name, "i") } : null,
      email ? { email: new RegExp(email, "i") } : null
    ].filter(Boolean)
  });

  res.json(users);
});
app.post("/api/users/upload-csv", csvUpload.single("file"), async (req, res) => {
  const results = [];

  fs.createReadStream(req.file.path)
    .pipe(csv())
    .on("data", (data) => results.push(data))
    .on("end", async () => {
      try {
        await User.insertMany(results);
        fs.unlinkSync(req.file.path); // cleanup
        res.json({ message: "CSV users imported", count: results.length });
      } catch (err) {
        res.status(500).json({ error: err.message });
      }
    });
});

// ✅ Delete user
app.delete("/api/users/:id", async (req, res) => {
  await User.findByIdAndDelete(req.params.id);
  res.json({ message: "User deleted" });
});

app.listen(process.env.PORT, () =>
  console.log(`Server running on port ${process.env.PORT}`)
);