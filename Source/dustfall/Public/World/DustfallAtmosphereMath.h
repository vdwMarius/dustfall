#pragma once
#include "CoreMinimal.h"

/** Pure normalized blends, shared by runtime and Dustfall.Core automation. */
struct FDustfallAtmosphereMath
{
    static float Smooth(float Low, float High, float Value)
    {
        const float X = FMath::Clamp((Value - Low) / FMath::Max(High - Low, SMALL_NUMBER), 0.f, 1.f);
        return X * X * (3.f - 2.f * X);
    }
    static float Night(float Time, float TwilightStart, float TwilightEnd)
    {
        // Environment director: sun pitch = 90*cos(2*pi*t); noon=.5, midnight=0.
        return Smooth(TwilightStart, TwilightEnd, FMath::Cos(2.f * PI * Time));
    }
    static float Weather(const FVector& Values, int32 WeatherIndex, float Storm)
    {
        // StormIntensity is interpolated by the director, including on storm exit.
        return FMath::Lerp(static_cast<float>(WeatherIndex == 0 ? Values.X : Values.Y),
            static_cast<float>(Values.Z), FMath::Clamp(Storm, 0.f, 1.f));
    }
    static float Approach(float Current, float Target, float Speed, float Delta)
    {
        return FMath::Lerp(Current, Target, 1.f - FMath::Exp(-FMath::Max(0.f, Speed) * FMath::Max(0.f, Delta)));
    }
    static float Wrap(float Position, float HalfExtent)
    {
        const float Size = FMath::Max(2.f * HalfExtent, SMALL_NUMBER);
        return FMath::Fmod(FMath::Fmod(Position + HalfExtent, Size) + Size, Size) - HalfExtent;
    }
    static float CombinedTransmittance(float Density, float DistanceCM, float StartCM, float MaxOpacity,
        float VolumetricDistanceCM, float Extinction)
    {
        // VolumetricFog.usf: extinction=rho/1000 * .5 * scale, integrated with exp().
        // HeightFogCommon.ush: analytic ray excludes the volumetric ViewZ range.
        const float NearDistance = FMath::Min(FMath::Max(0.f, DistanceCM), FMath::Max(0.f, VolumetricDistanceCM));
        const float Near = FMath::Exp(-Density / 1000.f * .5f * Extinction * NearDistance);
        return Near * HorizontalTransmittance(Density, DistanceCM, FMath::Max(StartCM, VolumetricDistanceCM), MaxOpacity);
    }
    static float SheetEdge(float U, float V)
    {
        // Same compact support as material: radius .42 leaves an 8% zero border.
        const float R2 = FMath::Square(U - .5f) + FMath::Square(V - .5f);
        return FMath::Square(FMath::Clamp(1.f - R2 / (.42f * .42f), 0.f, 1.f));
    }
    static float HorizontalTransmittance(float Density, float DistanceCM, float StartCM, float MaxOpacity)
    {
        // HeightFogCommon.ush: horizontal integral uses ln(2), followed by exp2.
        const float Integral = Density / 1000.f * FMath::Loge(2.f) * FMath::Max(0.f, DistanceCM - StartCM);
        return FMath::Max(FMath::Exp2(-Integral), 1.f - MaxOpacity);
    }
};
