const mongoose = require("mongoose");

const userSchema = new mongoose.Schema({
  name: { type: String, index: true },
  email: { type: String, index: true },
  age: Number,
  city: String,
  image: String,
  createdAt: { type: Date, default: Date.now }
});

module.exports = mongoose.model("User", userSchema);