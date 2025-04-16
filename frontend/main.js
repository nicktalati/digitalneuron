// frontend/main.js
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

// --- Configuration ---
// TODO: Replace hardcoded API URL with relative path after setting up CloudFront forwarding
const API_BASE_URL = 'https://le38xgfdkg.execute-api.us-east-1.amazonaws.com'; // Use your actual URL
const TILE_KEY = 'sphere';
const MAX_LOD_LEVEL = 4; // We now have LODs 0, 1, 2, 3, 4

// Define distance thresholds for switching LODs (adjust these values!)
// Closer distances use lower LOD numbers (higher detail)
const LOD_THRESHOLDS = [1.3, 2, 3, 4,];
const DEBOUNCE_DELAY = 2; // Milliseconds to wait after camera stops moving

// --- DOM Elements ---
const loadingIndicator = document.getElementById('loading-indicator');
// Remove buttons, we don't need them anymore
const controlsDiv = document.getElementById('controls');
if (controlsDiv) controlsDiv.remove(); // Clean up old UI

// --- Three.js Setup ---
let scene, camera, renderer, controls, currentModel = null, currentWireframe = null; // Add currentWireframe
const loader = new GLTFLoader();

// --- Define Materials ---
// White material for the main sphere surface
const sphereMaterial = new THREE.MeshBasicMaterial({
    color: 0xffffff, // White
});

// Black material for the wireframe edges
const wireframeMaterial = new THREE.LineBasicMaterial({
    color: 0x000000, // Black
    linewidth: 1, // Adjust thickness as needed (might not work on all platforms)
});

// --- LOD Management State ---
let currentVisibleLOD = -1; // Start with no LOD loaded
let targetLOD = -1;
let isLoading = false;
let debounceTimeout = null;

function initThree() {
    // Scene
    scene = new THREE.Scene();
    // --- Change Background to White ---
    scene.background = new THREE.Color(0xffffff); // White background

    // Camera
    camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.01, 1000);
    camera.position.z = 10;

    // Renderer
    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(window.devicePixelRatio); // Improve sharpness on high DPI displays
    renderer.setSize(window.innerWidth, window.innerHeight);
    document.body.appendChild(renderer.domElement);

    // Lights (Adjust intensity/color slightly for white material)
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.8); // Slightly brighter ambient
    scene.add(ambientLight);
    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.7); // Slightly less intense directional
    directionalLight.position.set(5, 10, 7.5);
    scene.add(directionalLight);
    const directionalLight2 = new THREE.DirectionalLight(0xffffff, 0.3); // Add another light from different angle
    directionalLight2.position.set(-5, -5, -5);
    scene.add(directionalLight2);


    // Controls
    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.minDistance = 1.01;

    // Event Listener & Resize (Same)
    controls.addEventListener('change', onCameraChange);
    window.addEventListener('resize', onWindowResize, false);

    // Start animation loop
    animate();

    // Initial Load (Same)
    checkAndLoadLOD();
}

function onWindowResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
}

function animate() {
    requestAnimationFrame(animate);
    const needsUpdate = controls.update(); // Required if damping enabled, returns true if view changed

    // Alternative check (less efficient but simpler than event listener sometimes):
    // checkAndLoadLOD(); // Check on every frame (can be too frequent)

    renderer.render(scene, camera);
}

// --- Dynamic LOD Logic ---

// Function to determine the target LOD based on distance
function determineTargetLOD() {
    // Calculate distance from camera to the origin (controls.target)
    const distance = camera.position.distanceTo(controls.target);
    // console.log("Distance:", distance); // For debugging thresholds

    for (let i = 0; i < LOD_THRESHOLDS.length; i++) {
        if (distance < LOD_THRESHOLDS[i]) {
            return i; // Return the LOD index (0 to MAX_LOD_LEVEL - 1)
        }
    }
    // If distance is greater than all thresholds, use the lowest detail LOD
    return MAX_LOD_LEVEL;
}

// Debounced function to check LOD and trigger load if needed
function checkAndLoadLOD() {
    clearTimeout(debounceTimeout); // Clear any pending load trigger

    debounceTimeout = setTimeout(() => {
        targetLOD = determineTargetLOD();
        // console.log(`Target LOD: ${targetLOD}, Current LOD: ${currentVisibleLOD}, IsLoading: ${isLoading}`);

        if (targetLOD !== currentVisibleLOD && !isLoading) {
             loadLOD(targetLOD);
        }
    }, DEBOUNCE_DELAY);
}

// Call checkAndLoadLOD whenever the camera potentially changes
function onCameraChange() {
    checkAndLoadLOD();
}


// --- API and Loading Logic (Modified loadLOD) ---

async function getTileUrl(lod) {
    // Check if LOD is valid before making API call
    if (lod < 0 || lod > MAX_LOD_LEVEL) {
        console.error(`Invalid LOD level requested: ${lod}`);
        return null;
    }
    const apiUrl = `${API_BASE_URL}/api/v1/tile/${lod}/${TILE_KEY}`;
    // console.log(`Fetching tile URL from: ${apiUrl}`); // Less verbose logging now
    try {
        const response = await fetch(apiUrl);
        if (!response.ok) {
            throw new Error(`API Error: ${response.status} ${response.statusText} for ${apiUrl}`);
        }
        const data = await response.json();
        if (!data.tileUrl) {
            throw new Error(`API response missing 'tileUrl' for ${apiUrl}`);
        }
        // console.log("Received pre-signed URL:", data.tileUrl);
        return data.tileUrl;
    } catch (error) {
        console.error("Failed to get tile URL:", error);
        // Don't alert here, let loadLOD handle UI feedback
        return null;
    }
}

async function loadGLB(url) {
    return new Promise((resolve, reject) => {
        loader.load(url, resolve, undefined, reject); // Simpler call using default callbacks
    }).then(gltf => {
        console.log("GLB loaded successfully from S3");
        return gltf.scene; // Return the scene object on success
    }).catch(error => {
        // Process error from loader.load's reject callback
        console.error('Error loading GLB from pre-signed URL:', error);
        const displayUrl = url.length > 100 ? url.substring(0, 100) + '...' : url;
        if (error instanceof ErrorEvent || (error.target && error.target.status)) { // Network/HTTP errors often wrapped
            const status = error.target ? error.target.status : 'Network Error';
            throw new Error(`Failed to load tile from S3 (${status}). URL: ${displayUrl}`);
        } else {
            throw new Error(`An error occurred loading the GLB model. URL: ${displayUrl}`);
        }
    });
}


async function loadLOD(lodToLoad) {
    if (isLoading || lodToLoad < 0 || lodToLoad > MAX_LOD_LEVEL) {
        console.warn(`Load request ignored: isLoading=${isLoading}, requestedLOD=${lodToLoad}`);
        return;
    }
    console.log(`Attempting to load LOD ${lodToLoad}`);
    isLoading = true;
    loadingIndicator.style.display = 'block';

    try {
        const tileUrl = await getTileUrl(lodToLoad);
        if (!tileUrl) throw new Error(`Could not retrieve URL for LOD ${lodToLoad}`);

        const loadedScene = await loadGLB(tileUrl); // loadGLB now returns the loaded THREE.Scene

        // --- Critical Check (Same) ---
        if (targetLOD !== lodToLoad) {
            console.log(`Load completed for LOD ${lodToLoad}, but target changed to ${targetLOD}. Discarding.`);
            // TODO: Dispose loadedScene resources
            return;
        }

        // --- Apply Materials and Create Wireframe ---
        let newModel = null;
        let newWireframe = null;

        loadedScene.traverse((child) => {
            if (child.isMesh) {
                 // Found the mesh! Assign the white material
                 child.material = sphereMaterial;
                 newModel = child; // Assume first mesh found is our sphere

                 // Create wireframe geometry from the mesh's geometry
                 const wireframeGeom = new THREE.WireframeGeometry(child.geometry);
                 newWireframe = new THREE.LineSegments(wireframeGeom, wireframeMaterial);

                 // Optional: Slightly offset wireframe to prevent z-fighting
                 // newWireframe.renderOrder = 1; // Render after the main mesh
                 // sphereMaterial.polygonOffset = true;
                 // sphereMaterial.polygonOffsetFactor = 1;
                 // sphereMaterial.polygonOffsetUnits = 1;
            }
        });

        if (!newModel) {
            throw new Error("No mesh found within the loaded GLB scene.");
        }

        // --- Remove Previous Models ---
        if (currentModel) {
            scene.remove(currentModel);
            // TODO: Proper disposal of old model's geometry/material
        }
        if (currentWireframe) {
            scene.remove(currentWireframe);
             // TODO: Proper disposal of old wireframe's geometry/material
             currentWireframe.geometry.dispose();
             // wireframeMaterial doesn't need disposal unless textures used
        }

        // --- Add New Models ---
        currentModel = newModel;
        currentWireframe = newWireframe; // Store the new wireframe

        scene.add(currentModel);
        scene.add(currentWireframe); // Add wireframe to the scene

        currentVisibleLOD = lodToLoad;
        console.log(`LOD ${lodToLoad} model and wireframe added to scene.`);

    } catch (error) {
        console.error(`Failed to load LOD ${lodToLoad}:`, error);
    } finally {
        isLoading = false;
        loadingIndicator.style.display = 'none';
        checkAndLoadLOD();
    }
}

initThree();
