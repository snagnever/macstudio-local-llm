import{S as e,a8 as t,B as n,a9 as a,D as i}from"./index-Bvl3HpW6.js";const r="volumetricLightingRenderVolumeVertexShader",s=`#include<__decl__sceneVertex>
#include<__decl__meshVertex>
attribute vec3 position;varying vec4 vWorldPos;void main(void) {vec4 worldPos=world*vec4(position,1.0);vWorldPos=worldPos;gl_Position=viewProjection*worldPos;}
`;e.ShadersStore[r]||(e.ShadersStore[r]=s);const c=[t,n,a,i];for(const o of c)e.IncludesShadersStore[o.name]||(e.IncludesShadersStore[o.name]=o.shader);const l={name:r,shader:s};export{l as volumetricLightingRenderVolumeVertexShader};
