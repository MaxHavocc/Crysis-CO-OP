#ifndef _CoopCutsceneSystem_H_
#define _CoopCutsceneSystem_H_
 
#include <IViewSystem.h>
#include <IMovieSystem.h>
 
class CCoopCutsceneSystem : public IViewSystemListener
{
private:
    static CCoopCutsceneSystem s_instance;
    CCoopCutsceneSystem();
    ~CCoopCutsceneSystem();
 
public:
    // Gets the static instance
    static inline CCoopCutsceneSystem* GetInstance() {
        return &s_instance;
    }
 
public:
    // Summary:
    //  Registers the system to listen to IViewSystem.
    void Register();
    // Summary:
    //  Unregisters the system from listening to IViewSystem.
    void Unregister();
 
    // Summary:
    //  Updates the camera view.
    void Update(float fFrameTime);

    bool IsPlayingCutscene() const { return m_bPlayingCutscene; }
    bool IsAwaitingAshoreBoot() const { return m_bAwaitingAshoreBoot; }
    void SetAwaitingAshoreBoot(bool b) { m_bAwaitingAshoreBoot = b; }
    bool AreBothPlayersReady() const { return m_bBothPlayersReady; }
    void SetBothPlayersReady(bool b) { m_bBothPlayersReady = b; }
 
private:
    bool            m_bPlayingCutscene;
    bool            m_bPlayingCutsceneLastFrame;
    bool            m_bCutsceneBlending;
    bool            m_bAwaitingAshoreBoot;
    bool            m_bBothPlayersReady;
    EntityId        m_cameraEntityId;
    float           m_fCameraFOV;
 
public:
    // IViewSystemListener
    virtual bool OnBeginCutScene(IAnimSequence* pSeq, bool bResetFX);
    virtual bool OnEndCutScene(IAnimSequence* pSeq);
    virtual void OnPlayCutSceneSound(IAnimSequence* pSeq, ISound* pSound);
    virtual bool OnCameraChange(const SCameraParams& cameraParams);
    // ~IViewSystemListener
 
};
 
#endif // _CoopCutsceneSystem_H_
