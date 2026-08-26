/**
 * The camera.
 *
 * Words live at fixed positions in a 3D world; the camera flies between them.
 * Structurally that is a `perspective` root plus a single inverse transform —
 * moving the world by -camera. Every word then only has to declare where it
 * *is*, never where it should appear at a given moment.
 *
 * Framing model: at rest on a word, the camera travels `camFollowXY` of that
 * word's world offset. It therefore never perfectly centres a word — each one
 * lands in its own part of the frame, which is what makes the piece feel like a
 * camera move rather than a slideshow. `poseFromScreen()` inverts the
 * projection so a word can be authored by the screen position it should hold
 * when focused, which is what makes the safe zones checkable.
 */

import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {EASE, SpeedTrail} from '../overlays/lib';
import type {Layout} from '../theme';

/* ------------------------------------------------------------------ *
 * Types
 * ------------------------------------------------------------------ */

export type Vec3 = {x: number; y: number; z: number};

export type CameraPose = {
  x: number;
  y: number;
  z: number;
  rx: number;
  ry: number;
  rz: number;
};

/** A word's place in the world. */
export type Pose = {
  x: number;
  y: number;
  z: number;
  rx: number;
  ry: number;
  rz: number;
};

/** One leg of the flight plan: at `at` seconds, start flying to `pose`. */
export type CameraKey = {
  at: number;
  pose: Pose;
  /** flight duration in seconds */
  flight: number;
};

export type CameraDrift = {
  from: {x?: number; y?: number; z?: number; scale?: number};
  to: {x?: number; y?: number; z?: number; scale?: number};
  start: number;
  end: number;
};

export const ORIGIN: Pose = {x: 0, y: 0, z: 0, rx: 0, ry: 0, rz: 0};

/* ------------------------------------------------------------------ *
 * Projection
 * ------------------------------------------------------------------ */

const rad = (deg: number): number => (deg * Math.PI) / 180;

/** Rotate v by Rz(cz)*Ry(cy)*Rx(cx), matching CSS `rotateZ rotateY rotateX`. */
const rotate = (v: Vec3, cx: number, cy: number, cz: number): Vec3 => {
  const [sx, kx] = [Math.sin(rad(cx)), Math.cos(rad(cx))];
  const [sy, ky] = [Math.sin(rad(cy)), Math.cos(rad(cy))];
  const [sz, kz] = [Math.sin(rad(cz)), Math.cos(rad(cz))];

  // Rx
  let {x, y, z} = v;
  let ny = y * kx - z * sx;
  let nz = y * sx + z * kx;
  y = ny;
  z = nz;
  // Ry
  let nx = x * ky + z * sy;
  nz = -x * sy + z * ky;
  x = nx;
  z = nz;
  // Rz
  nx = x * kz - y * sz;
  ny = x * sz + y * kz;
  return {x: nx, y: ny, z};
};

/** Where a world point lands on screen, in px from the frame centre. */
export const project = (
  p: Vec3,
  cam: CameraPose,
  perspective: number,
): {x: number; y: number; scale: number} => {
  const r = rotate(
    {x: p.x - cam.x, y: p.y - cam.y, z: p.z - cam.z},
    -cam.rx,
    -cam.ry,
    -cam.rz,
  );
  // Guard against the point crossing the projection plane.
  const denom = Math.max(perspective - r.z, perspective * 0.15);
  const s = perspective / denom;
  return {x: r.x * s, y: r.y * s, scale: s};
};

/** The camera's resting pose when `pose` is the focus. */
export const restPose = (pose: Pose, l: Layout): CameraPose => ({
  x: pose.x * l.camFollowXY,
  y: pose.y * l.camFollowXY,
  z: pose.z * l.camFollowZ,
  rx: pose.rx * l.camFollowRot,
  ry: pose.ry * l.camFollowRot,
  rz: pose.rz * l.camFollowRot,
});

/**
 * Author a word by where it should sit on screen when the camera is on it.
 * Inverts the projection above, so `sx`/`sy` are real, checkable pixels.
 */
export const poseFromScreen = (
  args: {
    sx: number;
    sy: number;
    z?: number;
    rx?: number;
    ry?: number;
    rz?: number;
  },
  l: Layout,
): Pose => {
  const {sx, sy, z = 0, rx = 0, ry = 0, rz = 0} = args;
  const dz = z * (1 - l.camFollowZ);
  const s = l.perspective / Math.max(l.perspective - dz, l.perspective * 0.15);
  const k = (1 - l.camFollowXY) * s;
  return {x: sx / k, y: sy / k, z, rx, ry, rz};
};

/* ------------------------------------------------------------------ *
 * Flight plan
 * ------------------------------------------------------------------ */

const lerpPose = (a: CameraPose, b: CameraPose, p: number): CameraPose => ({
  x: a.x + (b.x - a.x) * p,
  y: a.y + (b.y - a.y) * p,
  z: a.z + (b.z - a.z) * p,
  rx: a.rx + (b.rx - a.rx) * p,
  ry: a.ry + (b.ry - a.ry) * p,
  rz: a.rz + (b.rz - a.rz) * p,
});

const easeAt = (p: number): number => EASE.expoInOut(Math.min(1, Math.max(0, p)));

/**
 * Camera pose at `sec`. Legs are expo-in-out and are separated by holds, so the
 * camera is either flying or perfectly still — never creeping linearly.
 */
export const poseAt = (
  sec: number,
  keys: CameraKey[],
  l: Layout,
  drifts: CameraDrift[] = [],
): {cam: CameraPose; scale: number} => {
  const rests = keys.map((k) => restPose(k.pose, l));

  let cam: CameraPose = rests[0];
  for (let i = 0; i < keys.length; i++) {
    if (sec < keys[i].at) break;
    const from = i === 0 ? rests[0] : rests[i - 1];
    const p = keys[i].flight <= 0 ? 1 : (sec - keys[i].at) / keys[i].flight;
    cam = lerpPose(from, rests[i], easeAt(p));
  }

  // Drifts are additive and each one holds at its end value, so a finished
  // drift keeps what it did rather than snapping back.
  let scale = 1;
  for (const drift of drifts) {
    const raw = (sec - drift.start) / Math.max(1e-6, drift.end - drift.start);
    const p = EASE.heavy(Math.min(1, Math.max(0, raw)));
    const f = drift.from;
    const to = drift.to;
    cam = {
      ...cam,
      x: cam.x + (f.x ?? 0) + ((to.x ?? 0) - (f.x ?? 0)) * p,
      y: cam.y + (f.y ?? 0) + ((to.y ?? 0) - (f.y ?? 0)) * p,
      z: cam.z + (f.z ?? 0) + ((to.z ?? 0) - (f.z ?? 0)) * p,
    };
    scale *= (f.scale ?? 1) + ((to.scale ?? 1) - (f.scale ?? 1)) * p;
  }

  return {cam, scale};
};

/**
 * Screen-space speed of the stage, in px/frame — what decides how much motion
 * blur the frame gets. Two probe points are projected under this frame's and
 * the previous frame's camera; the larger displacement wins, so a pure dolly
 * (which barely moves the centre but sweeps the corners) is not under-blurred.
 */
export const stageSpeed = (
  sec: number,
  prevSec: number,
  keys: CameraKey[],
  l: Layout,
  drifts: CameraDrift[] = [],
): number => {
  const now = poseAt(sec, keys, l, drifts);
  const before = poseAt(prevSec, keys, l, drifts);
  const probes: Vec3[] = [
    {x: 0, y: 0, z: 0},
    {x: 420, y: 420, z: 0},
    {x: -420, y: -420, z: -300},
  ];
  let max = 0;
  for (const probe of probes) {
    const a = project(probe, now.cam, l.perspective);
    const b = project(probe, before.cam, l.perspective);
    const dx = a.x * now.scale - b.x * before.scale;
    const dy = a.y * now.scale - b.y * before.scale;
    max = Math.max(max, Math.hypot(dx, dy));
  }
  return max;
};

/* ------------------------------------------------------------------ *
 * Component
 * ------------------------------------------------------------------ */

export const Camera3D: React.FC<{
  readonly layout: Layout;
  readonly keys: CameraKey[];
  readonly drifts?: CameraDrift[];
  /**
   * Extra px/frame contributed by elements that move on their own inside the
   * stage (slams, strikes, tumbles) so they are blurred like the camera is.
   */
  readonly speedHint?: number;
  readonly children: React.ReactNode;
}> = ({layout, keys, drifts = [], speedHint = 0, children}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const sec = frame / fps;

  const {cam, scale} = poseAt(sec, keys, layout, drifts);
  const speed = Math.max(
    stageSpeed(sec, Math.max(0, sec - 1 / fps), keys, layout, drifts),
    speedHint,
  );

  // Inverse camera: move the world by -camera, then un-rotate it.
  const world = [
    `rotateZ(${-cam.rz}deg)`,
    `rotateY(${-cam.ry}deg)`,
    `rotateX(${-cam.rx}deg)`,
    `translate3d(${-cam.x}px, ${-cam.y}px, ${-cam.z}px)`,
  ].join(' ');

  return (
    <SpeedTrail speed={speed}>
      <AbsoluteFill style={{transform: `scale(${scale})`, transformOrigin: '50% 50%'}}>
        <AbsoluteFill
          style={{
            perspective: layout.perspective,
            perspectiveOrigin: '50% 50%',
            transformStyle: 'preserve-3d',
          }}
        >
          <AbsoluteFill style={{transform: world, transformStyle: 'preserve-3d'}}>
            {children}
          </AbsoluteFill>
        </AbsoluteFill>
      </AbsoluteFill>
    </SpeedTrail>
  );
};

/**
 * The frame punch: a 1-frame 1.02 hit released over 4 frames. It wraps
 * *everything* — stage and card plates alike — because a camera punch is a
 * property of the shot, not of one layer.
 */
export const FramePunch: React.FC<{
  readonly punches: {at: number; amount: number}[];
  readonly children: React.ReactNode;
}> = ({punches, children}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  let scale = 1;
  for (const {at, amount} of punches) {
    const f = at * fps;
    scale *= interpolate(frame, [f - 1, f, f + 4], [1, 1 + amount, 1], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
      easing: EASE.expoOut,
    });
  }
  return (
    <AbsoluteFill style={{transform: `scale(${scale})`, transformOrigin: '50% 50%'}}>
      {children}
    </AbsoluteFill>
  );
};
