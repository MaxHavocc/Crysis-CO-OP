#ifndef __HUDFADER_H__
#define __HUDFADER_H__

#pragma once

#include "HUDObject.h"

class CHUDFader
{
public:
	CHUDFader()
	{
		m_pRenderer = gEnv->pRenderer;
		assert (m_pRenderer != 0);

		m_currentColor = Col_Black;
		m_targetColor = Col_Black;
		m_drawColor = Col_Black;
		m_pTexture = 0;
		m_bActive = false;
		m_duration = 0.0f;
		m_curTime = 0.0f;
		m_direction = 0;
		m_ticket = 0;
	}

	~CHUDFader()
	{
		SAFE_RELEASE(m_pTexture);
	}

	const char* GetDebugName() const
	{
		if (m_pTexture)
			return m_pTexture->GetName();
		return "<no texture>";
	}

	void Stop()
	{
		m_bActive = false;
	}

	void Reset()
	{
		m_ticket = 0;
		m_bActive = false;
	}

	bool IsActive() const { return m_bActive; }
	bool IsPlaying(int ticket) const { return m_ticket > 0 && m_ticket==ticket; }
	ColorF GetCurrentColor()
	{
		float curVal = 1.0;
		if (m_duration != 0.0f)
		{
			curVal = m_curTime / m_duration;
			curVal = CLAMP(curVal, 0.0f, 1.0f);
		}
		ColorF col;
		col.lerpFloat(m_currentColor, m_targetColor, curVal);
		return col;
	}

	int FadeIn(const ColorF& targetColor, float fDuration, bool bUseCurrentColor=true)
	{
		if (m_ticket == 0 || bUseCurrentColor == false)
		{
			m_currentColor = targetColor;
			m_currentColor.a = 1.0f;
		}
		else
			m_currentColor = GetCurrentColor();
		m_targetColor = targetColor;
		m_targetColor.a = 0.0f;
		m_duration = fDuration > 0.0 ? fDuration : 0.0f;
		m_curTime = 0.0f;
		m_direction = -1;
		m_bActive = true;
		return ++m_ticket;
	}

	int FadeOut(const ColorF& targetColor, float fDuration, const char* textureName="", bool bUseCurrentColor=true)
	{
		SetTexture(textureName);
		if (m_ticket == 0 || bUseCurrentColor == false)
		{
			m_currentColor = targetColor;
			m_currentColor.a = 0.0f;
		}
		else
			m_currentColor = GetCurrentColor();
		m_targetColor = targetColor;
		m_targetColor.a = 1.0f;
		m_duration = fDuration > 0.0 ? fDuration : 0.0f;
		m_curTime = 0.0f;
		m_direction = 1;
		m_bActive = true;
		return ++m_ticket;
	}

	virtual void Update(float fDeltaTime)
	{
		if (m_bActive == false)
			return;

		if (m_duration == 0.0f || m_curTime >= m_duration)
		{
			if (m_direction == -1)
			{
				m_bActive = false;
				m_currentColor = m_targetColor;
			}
			m_currentColor = m_targetColor;
			m_ticket = 0;
		}
		m_drawColor = GetCurrentColor();
		m_curTime+=fDeltaTime;
	}

	virtual void Draw()
	{
		if (m_bActive == false)
			return;

		m_pRenderer->Draw2dImage(0.0f,0.0f,800.0f,600.0f,
			m_pTexture ? m_pTexture->GetTextureID() : 0,
			0.0f,1.0f,1.0f,0.0f, // tex coords
			0.0f, // angle
			m_drawColor.r, m_drawColor.g, m_drawColor.b, m_drawColor.a
			);
	}

	static ITexture* LoadTexture(const char* textureName)
	{
		if (gEnv->pRenderer)
			return gEnv->pRenderer->EF_LoadTexture(textureName,FT_DONT_ANISO|FT_DONT_RELEASE,eTT_2D);
		else
			return 0;
	}
protected:
	void SetTexture(const char* textureName)
	{
		if (m_pTexture && textureName && strcmp(textureName, m_pTexture->GetName()) == 0)
			return;

		SAFE_RELEASE(m_pTexture);
		if (textureName == 0 || *textureName == 0)
			return;

		m_pTexture = LoadTexture(textureName);
		if (m_pTexture != 0)
			m_pTexture->SetClamp(true);
	}

protected:
	IRenderer			*m_pRenderer;
	ColorF         m_currentColor;
	ColorF         m_targetColor;
	ColorF         m_drawColor;
	ITexture      *m_pTexture;
	float          m_duration;
	float          m_curTime;
	int            m_direction;
	int            m_ticket;
	bool           m_bActive;
};

CHUDFader* GetHUDFader(int group);

#endif // __HUDFADER_H__
