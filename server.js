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
app.use(express.urlencoded({ extended: true }));
app.use(express.static("public"));
app.use("/uploads", express.static("uploads"));

/* ---------------- MongoDB ---------------- */

mongoose
.connect(process.env.MONGO_URI)
.then(() => console.log("MongoDB Connected"))
.catch(err => console.log(err));

/* ---------------- Multer Config ---------------- */

const storage = multer.diskStorage({
  destination: "uploads/",
  filename: (req, file, cb) => {
    const safeName = path.basename(file.originalname);
    cb(null, Date.now() + "-" + safeName);
  }
});

const upload = multer({
  storage,
  limits: { fileSize: 5 * 1024 * 1024 } // 5MB
});
const csvUpload = multer({ dest: "uploads/" });

/* ---------------- CREATE USER ---------------- */

app.post("/api/users", upload.single("image"), async (req, res) => {
  try {

    if (!req.body.name || !req.body.email) {
      return res.status(500).json({ error: "Missing required fields" });
    }

    const user = new User({
      name: req.body.name,
      email: req.body.email,
      age: req.body.age,
      city: req.body.city,
      image: req.file ? `/uploads/${req.file.filename}` : null
    });

    await user.save();

    res.json({
      message: "User saved",
      user
    });

  } catch (err) {

  if (err.code === 11000) {
    return res.status(500).json({ error: "Duplicate email" });
  }

  res.status(500).json({ error: err.message });
}
});

/* ---------------- GET USERS ---------------- */

app.get("/api/users", async (req, res) => {
  try {
    const users = await User.find();
    res.json(users);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

/* ---------------- SEARCH USERS ---------------- */

app.get("/api/users/search", async (req, res) => {
  try {

    const name = req.query.name;
    const email = req.query.email;

    const query = {};

    // Only allow string values (protects from NoSQL injection)
    if (typeof name === "string" && name.trim() !== "") {
      query.name = { $regex: name, $options: "i" };
    }

    if (typeof email === "string" && email.trim() !== "") {
      query.email = { $regex: email, $options: "i" };
    }

    // If request has NO query parameters → return all users
    if (Object.keys(req.query).length === 0) {
      const users = await User.find();
      return res.json(users);
    }

    // If query parameters exist but are invalid (e.g. name[$ne])
    if (Object.keys(query).length === 0) {
      return res.json([]);
    }

    const users = await User.find(query);
    res.json(users);

  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

/* ---------------- CSV IMPORT ---------------- */

app.post("/api/users/upload-csv", csvUpload.single("file"), async (req, res) => {

  if (!req.file) {
    return res.status(400).json({ error: "No CSV file uploaded" });
  }

  const results = [];

  const stream = fs.createReadStream(req.file.path)
    .pipe(csv());

  stream.on("data", (data) => {
    results.push({
      name: data.name,
      email: data.email,
      age: data.age,
      city: data.city
    });
  });

  stream.on("end", async () => {
    try {

      if (results.some(r => !r.email)) {
        fs.unlinkSync(req.file.path);
        return res.status(500).json({ error: "Missing email column" });
      }

      await User.insertMany(results);

      fs.unlinkSync(req.file.path);

      return res.json({
        message: "CSV users imported",
        count: results.length
      });

    } catch (err) {

      fs.unlinkSync(req.file.path);

      return res.status(500).json({ error: err.message });

    }
  });

  stream.on("error", (err) => {
    fs.unlinkSync(req.file.path);
    return res.status(500).json({ error: "CSV processing failed" });
  });

});

/* ---------------- DELETE USER ---------------- */

app.delete("/api/users/:id", async (req, res) => {

  try {

    await User.findByIdAndDelete(req.params.id);

    res.json({
      message: "User deleted"
    });

  } catch (err) {

    res.status(500).json({ error: err.message });

  }

});

/* ---------------- BULK DELETE ---------------- */

app.delete("/api/users", async (req, res) => {

  try {

    const { ids } = req.body;

    if (!ids || !Array.isArray(ids) || ids.length === 0) {
      return res.status(400).json({
        message: "No user IDs provided"
      });
    }

    const result = await User.deleteMany({
      _id: { $in: ids }
    });

    res.json({
      message: "Users deleted successfully",
      deletedCount: result.deletedCount
    });

  } catch (err) {

    res.status(500).json({ error: err.message });

  }

});

/* ---------------- UPDATE USER ---------------- */

app.put("/api/users/:id", upload.single("image"), async (req, res) => {

  try {

    const updateData = {};

    if (req.body.name) updateData.name = req.body.name;
    if (req.body.email) updateData.email = req.body.email;
    if (req.body.age) updateData.age = req.body.age;
    if (req.body.city) updateData.city = req.body.city;

    if (req.file) {
      updateData.image = `/uploads/${req.file.filename}`;
    }

    const updatedUser = await User.findByIdAndUpdate(
      req.params.id,
      updateData,
      { new: true }
    );

    res.json({
      message: "User updated successfully",
      user: updatedUser
    });

  } catch (err) {

    res.status(500).json({ error: err.message });

  }

});

/* ---------------- START SERVER ---------------- */

app.listen(process.env.PORT, () => {
  console.log(`Server running on port ${process.env.PORT}`);
});