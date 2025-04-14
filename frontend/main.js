// frontend/main.js
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

// --- Configuration ---
// TODO: Replace hardcoded API URL with relative path after setting up CloudFront forwarding
const API_BASE_URL = 'https://le38xgfdkg.execute-api.us-east-1.amazonaws.com'; // Paste the URL from CDK output
const TILE_KEY = 'sphere'; // The key we used in the asset pipeline

// --- DOM Elements ---
const btnLoadLod0 = document.getElementById('load-lod0');
const btnLoadLod1 = document.getElementById('load-lod1');
const loadingIndicator = document.getElementById('loading-indicator');

// --- Three.js Setup ---
let scene, camera, renderer, controls, currentModel = null;
const loader = new GLTFLoader();

function initThree() {
    // Scene
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x222222);

    // Camera
    camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.z = 5; // Adjust starting position as needed

    // Renderer
    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    document.body.appendChild(renderer.domElement);

    // Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambientLight);
    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(5, 10, 7.5);
    scene.add(directionalLight);

    // Controls
    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true; // Optional: smooths camera movement

    // Handle window resize
    window.addEventListener('resize', onWindowResize, false);

    // Start animation loop
    animate();
}

function onWindowResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
}

function animate() {
    requestAnimationFrame(animate);
    controls.update(); // Required if damping is enabled
    renderer.render(scene, camera);
}

// --- API and Loading Logic ---

async function getTileUrl(lod) {
    const apiUrl = `${API_BASE_URL}/api/v1/tile/${lod}/${TILE_KEY}`;
    console.log(`Fetching tile URL from: ${apiUrl}`);
    try {
        const response = await fetch(apiUrl);
        if (!response.ok) {
            throw new Error(`API Error: ${response.status} ${response.statusText}`);
        }
        const data = await response.json();
        if (!data.tileUrl) {
            throw new Error("API response missing 'tileUrl'");
        }
        console.log("Received pre-signed URL:", data.tileUrl);
        return data.tileUrl;
    } catch (error) {
        console.error("Failed to get tile URL:", error);
        alert(`Error fetching tile URL: ${error.message}`); // Simple error feedback
        return null;
    }
}

async function loadGLB(url) {
    return new Promise((resolve, reject) => {
        loader.load(
            url,
            // onLoad callback
            (gltf) => {
                console.log("GLB loaded successfully from S3");
                resolve(gltf.scene); // Resolve with the scene object
            },
            // onProgress callback (optional)
            (xhr) => {
                // console.log((xhr.loaded / xhr.total * 100) + '% loaded');
            },
            // onError callback
            (error) => {
                console.error('Error loading GLB from pre-signed URL:', error);
                // Check if it might be a 403/404 from S3
                if (error.message.includes('403') || error.message.includes('404')) {
                     reject(new Error(`Failed to load tile from S3 (403/404). URL: ${url.substring(0,100)}...`));
                } else {
                     reject(new Error(`An error occurred loading the GLB model. URL: ${url.substring(0,100)}...`));
                }
            }
        );
    });
}


async function loadLOD(lod) {
    console.log(`Attempting to load LOD ${lod}`);
    loadingIndicator.style.display = 'block';
    try {
        const tileUrl = await getTileUrl(lod);
        if (!tileUrl) {
            loadingIndicator.style.display = 'none';
            return; // Error handled in getTileUrl
        }

        const model = await loadGLB(tileUrl);

        // Remove previous model if it exists
        if (currentModel) {
            scene.remove(currentModel);
            // TODO: Dispose of geometry/materials if needed for memory management later
        }

        // Add new model
        currentModel = model;
        // You might need to center/scale the model depending on how it was exported
        // model.position.set(0, 0, 0);
        scene.add(currentModel);
        console.log(`LOD ${lod} model added to scene.`);

    } catch (error) {
        console.error(`Failed to load LOD ${lod}:`, error);
        alert(`Error loading model: ${error.message}`); // Simple error feedback
    } finally {
         loadingIndicator.style.display = 'none';
    }
}

// --- Event Listeners ---
btnLoadLod0.addEventListener('click', () => loadLOD(0));
btnLoadLod1.addEventListener('click', () => loadLOD(1));

// --- Initialization ---
initThree();
// Optionally load a default LOD on startup
// loadLOD(1); // Load low-detail initially?
