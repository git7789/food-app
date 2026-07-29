# 🍔 Foodies: Mobile Order & Instant Assembly Platform

**Project Type:** Full-Stack Cloud Web Application  
**Developer:** Nokutenda Majora 

## ⚠️ Project Status & Exclusivity: Proof of Concept
**Disclaimer:** This current repository represents a fully functional, cloud-hosted web prototype. It was custom-engineered from the ground up specifically as a demonstration of concept for modernizing local fast-food operations. It does not utilize off-the-shelf restaurant templates, nor does it represent a finalized commercial product for any specific brand. The development of native mobile applications (iOS/Android) and the integration of live payment gateways are currently deferred pending official project approval, partnership validation, and a commercial "go-ahead."

## 📖 Project Overview
Foodies is a modern, responsive web application designed to eliminate traditional restaurant waiting lines. The system allows customers to place orders from their mobile devices and instantly syncs their tickets with a live Kitchen Display System (KDS). Once the food is ready, customers scan a unique, cryptographically secure QR token at the counter for immediate dispatch. 

## 🏗️ System Architecture
The platform is separated into two distinct environments: a public-facing customer portal and a secure, role-based internal network for restaurant staff.

* **The Customer Experience (Public):** A highly responsive UI where users can browse the menu, manage a cart, and place orders. It includes a custom multi-step authentication flow and receipt history management.
* **The Staff Experience (Protected):** An internal suite of tools locked behind staff authentication. It features a live Kitchen Display System (KDS), a Dispatch Scanner, and a public TV Order Board for queue tracking.

## 💻 Key Technologies 

| Technology | Implementation Details |
| :--- | :--- |
| **Frontend UI** | HTML5, Tailwind CSS, and custom pure CSS glassmorphism. |
| **Frontend Logic** | React.js (via CDN) utilizing functional components and state hooks. |
| **Backend API** | Python and Flask serving RESTful endpoints for state and order handling. |
| **Database** | MongoDB Atlas (NoSQL) for permanent cloud data persistence. |
| **Cloud Hosting** | Render with Gunicorn acting as the production WSGI HTTP server. |
| **Security** | Python `hashlib` (SHA-256) for password hashing and `hmac` for QR payload signatures. |

## 🚀 Core Features
* **Real-Time Queue Syncing:** The system uses asynchronous fetching to instantly update the Kitchen Display System and the public Order Board the second a customer checks out. 
* **Cryptographic QR Tokens:** Each order generates a unique QR code embedded with an HMAC-SHA256 signature, ensuring that tickets cannot be forged or duplicated.
* **Multi-Step Authentication:** A custom-built registration flow that supports email verification simulations and encrypted password storage.
* **Cloud Persistence:** The backend is fully integrated with MongoDB Atlas, preventing data loss during ephemeral server restarts.
* **Mock Integrations:** Features built-in mock systems for SMS ticket notifications and email verification, ensuring the logic is production-ready without requiring paid API subscriptions.
