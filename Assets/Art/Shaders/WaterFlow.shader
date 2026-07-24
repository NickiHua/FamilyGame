Shader "FantacyCentry/WaterFlow"
{
    // Flow-map water shader for a baked top-down HD battle map (URP, SpriteRenderer).
    //
    // The whole map is one flat sprite. This shader animates ONLY the pixels marked
    // by _WaterMask, advecting procedural ripples along _FlowMap (so the river flows
    // down its bend). It uses the classic flow-map phase-blend trick (two half-cycle
    // offset samples cross-faded) so the scrolling never shows a repeat seam, even
    // though the ripple noise itself is not tileable.
    Properties
    {
        [PerRendererData] _MainTex ("Sprite (HD map)", 2D) = "white" {}
        _WaterMask   ("Water Mask (R)", 2D) = "black" {}
        _FlowMap     ("Flow Map (RG)", 2D) = "grey" {}

        _FlowSpeed      ("Flow Speed", Range(0, 0.5)) = 0.05
        _FlowStrength   ("Flow Advection", Range(0, 1)) = 0.22
        _NoiseScale     ("Ripple Scale", Range(1, 60)) = 30
        _RippleStrength ("Ripple Height", Range(0, 3)) = 0.5
        _RefractStrength("Refraction (UV warp)", Range(0, 0.02)) = 0.0015

        _SpecColor      ("Sparkle Color", Color) = (1, 1, 1, 1)
        _SpecStrength   ("Sparkle Strength", Range(0, 2)) = 0.14
        _SpecPower      ("Sparkle Sharpness", Range(1, 32)) = 14

        [HideInInspector] _RendererColor ("RendererColor", Color) = (1,1,1,1)
    }

    SubShader
    {
        Tags
        {
            "RenderPipeline" = "UniversalPipeline"
            "Queue" = "Transparent"
            "RenderType" = "Transparent"
            "IgnoreProjector" = "True"
            "CanUseSpriteAtlas" = "True"
        }

        Cull Off
        ZWrite Off
        Blend SrcAlpha OneMinusSrcAlpha

        Pass
        {
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            struct Attributes
            {
                float4 positionOS : POSITION;
                float4 color      : COLOR;
                float2 uv         : TEXCOORD0;
            };

            struct Varyings
            {
                float4 positionHCS : SV_POSITION;
                float4 color       : COLOR;
                float2 uv          : TEXCOORD0;
            };

            TEXTURE2D(_MainTex);   SAMPLER(sampler_MainTex);
            TEXTURE2D(_WaterMask); SAMPLER(sampler_WaterMask);
            TEXTURE2D(_FlowMap);   SAMPLER(sampler_FlowMap);

            CBUFFER_START(UnityPerMaterial)
                float  _FlowSpeed;
                float  _FlowStrength;
                float  _NoiseScale;
                float  _RippleStrength;
                float  _RefractStrength;
                float4 _SpecColor;
                float  _SpecStrength;
                float  _SpecPower;
                float4 _RendererColor;
            CBUFFER_END

            // --- cheap value noise (not tileable; seam hidden by phase blend) -----
            float hash21(float2 p)
            {
                p = frac(p * float2(123.34, 345.45));
                p += dot(p, p + 34.345);
                return frac(p.x * p.y);
            }

            float vnoise(float2 p)
            {
                float2 i = floor(p);
                float2 f = frac(p);
                f = f * f * (3.0 - 2.0 * f);
                float a = hash21(i);
                float b = hash21(i + float2(1, 0));
                float c = hash21(i + float2(0, 1));
                float d = hash21(i + float2(1, 1));
                return lerp(lerp(a, b, f.x), lerp(c, d, f.x), f.y);
            }

            float ripple(float2 p)
            {
                // two-octave fbm -> smooth wavey height
                float h = vnoise(p) * 0.65 + vnoise(p * 2.03 + 7.1) * 0.35;
                return h;
            }

            // Sample the advected ripple height at a flow phase, return height.
            float sampleFlow(float2 uv, float2 flowDir, float phase)
            {
                float2 p = uv * _NoiseScale - flowDir * _FlowStrength * phase * _NoiseScale;
                return ripple(p);
            }

            Varyings vert(Attributes IN)
            {
                Varyings OUT;
                OUT.positionHCS = TransformObjectToHClip(IN.positionOS.xyz);
                OUT.uv = IN.uv;
                OUT.color = IN.color * _RendererColor;
                return OUT;
            }

            float4 frag(Varyings IN) : SV_Target
            {
                float2 uv = IN.uv;
                float mask = SAMPLE_TEXTURE2D(_WaterMask, sampler_WaterMask, uv).r;

                // Flow direction (0.5 neutral -> zero). G is +down in image space,
                // sprite V is flipped, so negate Y to match on-screen flow.
                float2 flow = SAMPLE_TEXTURE2D(_FlowMap, sampler_FlowMap, uv).rg * 2.0 - 1.0;
                flow.y = -flow.y;

                float3 baseCol = SAMPLE_TEXTURE2D(_MainTex, sampler_MainTex, uv).rgb;
                float  baseA   = SAMPLE_TEXTURE2D(_MainTex, sampler_MainTex, uv).a;

                if (mask > 0.001)
                {
                    float t = _TimeParameters.x * _FlowSpeed;
                    float phase0 = frac(t);
                    float phase1 = frac(t + 0.5);
                    float blend  = abs(1.0 - 2.0 * phase0); // triangle 0..1..0

                    // Ripple height via finite differences -> pseudo normal (gradient).
                    float e = 1.0 / _NoiseScale;
                    float h0  = lerp(sampleFlow(uv, flow, phase0), sampleFlow(uv, flow, phase1), blend);
                    float hx  = lerp(sampleFlow(uv + float2(e, 0), flow, phase0), sampleFlow(uv + float2(e, 0), flow, phase1), blend);
                    float hy  = lerp(sampleFlow(uv + float2(0, e), flow, phase0), sampleFlow(uv + float2(0, e), flow, phase1), blend);
                    float2 grad = float2(hx - h0, hy - h0) * _RippleStrength;

                    // Gentle refraction: tiny UV warp so the painted water just shimmers.
                    float2 warp = grad * _RefractStrength;
                    float3 warped = SAMPLE_TEXTURE2D(_MainTex, sampler_MainTex, uv + warp * mask).rgb;
                    baseCol = lerp(baseCol, warped, mask);

                    // Sparkle: THIN, sparse glints from a finer, faster ripple band
                    // (narrow smoothstep -> streaks, not broad soapy blobs).
                    float hf = lerp(sampleFlow(uv * 2.1, flow, phase0),
                                    sampleFlow(uv * 2.1, flow, phase1), blend);
                    float glint = smoothstep(0.70, 0.95, hf);
                    glint = pow(glint, max(1.0, _SpecPower * 0.35));
                    baseCol += _SpecColor.rgb * (glint * _SpecStrength * mask);
                }

                float3 rgb = baseCol * IN.color.rgb;
                return float4(rgb, baseA * IN.color.a);
            }
            ENDHLSL
        }
    }

    Fallback "Sprites/Default"
}
